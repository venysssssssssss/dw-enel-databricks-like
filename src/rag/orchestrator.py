"""Orquestrador RAG: intent routing → retrieval → prompt assembly → LLM → citações.

Economia de tokens (ordem de impacto em CPU local):
1. **Intent routing** (regex) pula retrieval em saudação/out-of-scope.
2. **Doc-type filter** (retriever.route_doc_types) reduz chunks antes do vetor.
3. **Top-N curto** (default 5) no contexto. Chunk 480 tokens.
4. **History compactação** quando histórico > 6 turnos (só últimos 4 íntegros).
5. **Budget enforcement**: trunca passages para caber em `max_turn_tokens`.
6. **KV cache implícito do llama-cpp**: sistema idêntico entre turnos amortiza.
"""

from __future__ import annotations

import os
import re
import time
import json
from pathlib import Path
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, Literal

from src.common.llm_gateway import build_provider
from src.rag.answer_cache import CachedAnswer, resolve_known_answer
from src.rag.prompts import (
    SYSTEM_STATIC,
    build_messages,
    build_summarize_history_prompt,
)
from src.rag.cache.positive_cache import PositiveCache
from src.rag.retriever import HybridRetriever, Passage, route_doc_types
from src.rag.safety import (
    OUT_OF_SCOPE_MESSAGE,
    check_input,
    is_out_of_regional_scope,
    is_out_of_scope,
    sanitize_output,
)
from src.rag.telemetry import TurnTelemetry, hash_question, preview, record

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

    from src.common.llm_gateway import LLMProvider
    from src.rag.config import RagConfig

_GREETING_RE = re.compile(
    r"^\s*(olá|ola|oi+|bom\s*dia|boa\s*tarde|boa\s*noite|hello|hi|hey|e\s*aí)\b",
    re.IGNORECASE,
)

_CE_RE = re.compile(r"(ceará|cearense|fortaleza|\bce\b)", re.IGNORECASE)
_SP_RE = re.compile(r"(são paulo|paulista|\bsp\b)", re.IGNORECASE)

ANALYTICAL_INTENTS = {"analise_dados"}
_SUMMARY_MAX_CHARS = 800

OUT_OF_REGIONAL_SCOPE_MESSAGE = (
    "Este assistente responde apenas sobre as regionais **Ceará (CE)** e "
    "**São Paulo (SP)**. Para outras regiões, consulte o dashboard regional "
    "ou a equipe de dados."
)

INDIVIDUAL_CLIENT_MESSAGE = (
    "O dataset CE/SP é **agregado e anonimizado** — não há dados por cliente, "
    "UC ou instalação individual neste assistente. Posso responder sobre "
    "causas-raiz, assuntos, refaturamento, evolução mensal e grupo tarifário. "
    "Reformule a pergunta em termos de métrica agregada (ex.: "
    "\"Quais os principais motivos de reclamação?\")."
)

_INDIVIDUAL_CLIENT_RE = re.compile(
    r"\b(cliente|clientes|consumidor|consumidores|cpf|uc individual|"
    r"instalação|instalacao|medidor específico|número de telefone)\b",
    re.IGNORECASE,
)

_PROFILE_DETAIL_RE = re.compile(
    r"\b(perfil|data da fatura|fatura reclamada|emissão|emissao|vencimento|"
    r"tipo de medidor|medidor|valor médio|valor medio|tempo entre)\b",
    re.IGNORECASE,
)

_GENERIC_FALLBACK_RE = re.compile(
    r"(não encontrei essa informação|sem dados|não há dados indexados)",
    re.IGNORECASE,
)
_METER_REASON_QUERY_RE = re.compile(
    r"\b(motivo|motivos|causa|causas|assunto|assuntos)\b.*"
    r"\b(medidor(?:es)?|digital|analógic\w*|analogic\w*|ciclom\w*)\b|"
    r"\b(medidor(?:es)?|digital|analógic\w*|analogic\w*|ciclom\w*)\b.*"
    r"\b(motivo|motivos|causa|causas|assunto|assuntos)\b",
    re.IGNORECASE,
)
_REFAT_EXPLANATION_RE = re.compile(
    r"\brefaturamento\s+produtos\b.*\b(o que|por que|porque|recorrent)\b|"
    r"\b(o que|por que|porque|recorrent)\b.*\brefaturamento\s+produtos\b",
    re.IGNORECASE,
)
_DRILLDOWN_CANONICAL_ANCHORS = {
    "sp-causas-por-tipo-medidor",
    "sp-tipos-medidor",
    "sp-tipos-medidor-digitacao",
    "ce-reclamacoes-totais-assunto-causa",
    "ce-reclamacoes-totais-assuntos",
    "ce-reclamacoes-totais-refaturamento",
}

# Boosts determinísticos: cada regra casa a query e injeta cards canônicos na
# retrieval. Ordem importa — primeiros anchors têm prioridade visual no prompt.
# CE tem dois universos: (a) cards CE-total com 167k ordens reais e (b) cards
# CE+SP de erro_leitura rotulado. As regras abaixo casam primeiro os genéricos
# e depois a extensão CE-total é aplicada separadamente quando região=CE.
_CARD_BOOST_RULES: tuple[tuple[re.Pattern[str], tuple[str, ...]], ...] = (
    # Taxonomia consolidada (assunto + causa)
    (
        re.compile(
            r"\b(taxonomia|assunto\s*\+\s*causa|motivo consolidado|motivos consolidados)\b",
            re.IGNORECASE,
        ),
        ("motivos-taxonomia-ce-sp", "top-assuntos", "top-causas-raiz"),
    ),
    # Termo explícito de negócio (CE total): refaturamento produtos
    (
        re.compile(r"\brefaturamento\s+produtos\b", re.IGNORECASE),
        (
            "ce-reclamacoes-totais-assuntos",
            "ce-reclamacoes-totais-refaturamento",
            "ce-reclamacoes-totais-assunto-causa",
            "ce-reclamacoes-totais-mensal-assuntos",
            "motivos-taxonomia-ce-sp",
        ),
    ),
    # Motivos/causas por tipo de medidor (SP)
    (
        re.compile(
            r"\b(motivo|motivos|causa|causas|assunto|assuntos)\b.*"
            r"\b(medidor(?:es)?|digital|analógic\w*|analogic\w*|ciclom\w*)\b|"
            r"\b(medidor(?:es)?|digital|analógic\w*|analogic\w*|ciclom\w*)\b.*"
            r"\b(motivo|motivos|causa|causas|assunto|assuntos)\b",
            re.IGNORECASE,
        ),
        ("sp-causas-por-tipo-medidor", "sp-tipos-medidor", "sp-n1-causas"),
    ),
    # Tipos de medidor em casos de digitação (SP)
    (
        re.compile(
            r"\b(tipos?\s+de\s+medidor(?:es)?|medidores?)\b.*\b(digita\w*)\b|"
            r"\b(digita\w*)\b.*\b(tipos?\s+de\s+medidor(?:es)?|medidores?)\b",
            re.IGNORECASE,
        ),
        ("sp-tipos-medidor-digitacao", "sp-tipos-medidor", "sp-n1-causas"),
    ),
    # Tipos de medidor em SP (visão geral)
    (
        re.compile(
            r"\b(tipos?\s+de\s+medidor(?:es)?|medidores?\s+existentes|"
            r"tipo do medidor)\b",
            re.IGNORECASE,
        ),
        ("sp-tipos-medidor", "sp-perfil-assunto-lider", "sp-n1-top-instalacoes"),
    ),
    # Instalações com problemas de digitação
    (
        re.compile(
            r"\b(instala\w*|ucs?)\b.*\b(digita\w*)\b|"
            r"\b(digita\w*)\b.*\b(instala\w*|ucs?)\b",
            re.IGNORECASE,
        ),
        ("instalacoes-digitacao", "ce-top-instalacoes", "sp-n1-top-instalacoes"),
    ),
    # Causas-raiz / motivos principais
    (
        re.compile(
            r"\b(causa|causas|causa-raiz|causa raiz|motivo|motivos|"
            r"principal|principais|mais frequente|mais comum|mais gera|"
            r"o que mais)\b",
            re.IGNORECASE,
        ),
        ("top-causas-raiz", "top-assuntos"),
    ),
    # Causa evidenciada em observações (SP)
    (
        re.compile(
            r"\b(causa[ -]?raiz).*?\b(observa\w*|texto|devolutiva)\b|"
            r"\b(observa\w*|texto|devolutiva).*?\b(causa[ -]?raiz)\b",
            re.IGNORECASE,
        ),
        ("sp-causa-observacoes", "sp-n1-causas"),
    ),
    # Perfil detalhado do assunto líder (SP)
    (
        re.compile(
            r"\b(perfil|tipo de medidor|medidor|fatura reclamada|data da fatura|"
            r"valor médio da fatura|valor medio da fatura|emissão|emissao|vencimento|"
            r"tempo entre)\b",
            re.IGNORECASE,
        ),
        ("sp-perfil-assunto-lider", "sp-tipos-medidor", "sp-n1-assuntos"),
    ),
    # Instalações por regional
    (
        re.compile(
            r"\b(instala\w*|ucs?|clientes?).*\b(regional|região|regiao)\b|"
            r"\b(regional|região|regiao).*\b(instala\w*|ucs?|clientes?)\b",
            re.IGNORECASE,
        ),
        ("instalacoes-por-regional", "ce-top-instalacoes", "sp-n1-top-instalacoes"),
    ),
    # Sazonalidade
    (
        re.compile(
            r"\b(sazonalidade|sazonal|estacional|pico mensal|picos mensais)\b",
            re.IGNORECASE,
        ),
        ("sazonalidade-ce-sp", "evolucao-mensal"),
    ),
    # Reincidência por assunto
    (
        re.compile(
            r"\b(reincid\w*|recorr\w*|repeti\w* por assunto)\b",
            re.IGNORECASE,
        ),
        ("reincidencia-por-assunto", "top-assuntos"),
    ),
    # Dificuldade principal do cliente + medida recomendada
    (
        re.compile(
            r"\b(dificuldade|dor principal|medida|ação|acao|o que posso adotar|"
            r"plano de ação|plano de acao)\b",
            re.IGNORECASE,
        ),
        ("playbook-acoes-cliente", "top-assuntos", "top-causas-raiz"),
    ),
    # Assuntos / tipos de reclamação (genérico; vem após intents específicas)
    (
        re.compile(
            r"\b(assunto|assuntos|tipo de reclama|tipos de reclama|"
            r"categoria|categorias)\b",
            re.IGNORECASE,
        ),
        ("top-assuntos", "top-causas-raiz"),
    ),
    # Refaturamento / maior taxa
    (
        re.compile(
            r"\b(refatur|maior taxa|maior percentual|maior índice|"
            r"mais refatur)\b",
            re.IGNORECASE,
        ),
        ("refaturamento", "ce-vs-sp-refaturamento", "top-assuntos"),
    ),
    # Evolução temporal / repetição / mensal
    (
        re.compile(
            r"\b(mensal|mês|meses|tempo|evolu|série|serie|"
            r"repete|repetem|repetiç|longo do tempo|ao longo|"
            r"frequência temporal|pico|tendência|tendencia)\b",
            re.IGNORECASE,
        ),
        ("evolucao-mensal", "ce-vs-sp-mensal", "top-assuntos"),
    ),
    # Grupo tarifário
    (
        re.compile(r"\b(grupo|tarifári|tarifario|\bgb\b|\bga\b|grupo b|grupo a)\b", re.IGNORECASE),
        ("grupo-tarifario",),
    ),
    # Comparação CE vs SP
    (
        re.compile(
            r"\b(compar\w*|vs|versus|diferen\w+|entre ce e sp|entre sp e ce)\b",
            re.IGNORECASE,
        ),
        ("ce-vs-sp-causas", "ce-vs-sp-refaturamento", "ce-vs-sp-mensal"),
    ),
    # Visão geral / totais
    (
        re.compile(
            r"\b(total|totais|visão geral|visao geral|resumo|overview|quantas ordens)\b",
            re.IGNORECASE,
        ),
        ("visao-geral",),
    ),
    # Instalação / UC / cliente individual → cards de top-instalações (MVP)
    (
        re.compile(
            r"\b(instala\w*|\buc\b|ucs|cliente|clientes|consumidor|consumidores|"
            r"qual .* mais reclam\w*|quem .* mais reclam\w*|medidor)\b",
            re.IGNORECASE,
        ),
        ("ce-top-instalacoes", "sp-n1-top-instalacoes", "sp-tipos-medidor"),
    ),
    # Mês específico / ano-mês → cards mensais por assunto/causa
    (
        re.compile(
            r"(\b(janeiro|fevereiro|março|marco|abril|maio|junho|julho|agosto|"
            r"setembro|outubro|novembro|dezembro)\b|\b20(25|26)-\d{2}\b|"
            r"\bmês de\b|\bmes de\b|\bno mês\b|\bno mes\b|\bem 20(25|26)\b)",
            re.IGNORECASE,
        ),
        (
            "ce-reclamacoes-totais-mensal-assuntos",
            "ce-reclamacoes-totais-mensal-causas",
            "evolucao-mensal",
        ),
    ),
)


# Mapa query-keyword → card CE-total. Aplicado ADICIONALMENTE aos boosts
# genéricos quando a região detectada é CE (para priorizar o universo de 167k
# reclamações totais em vez do subset rotulado de erro_leitura).
_CE_TOTAL_BOOSTS: tuple[tuple[re.Pattern[str], tuple[str, ...]], ...] = (
    (
        re.compile(
            r"\b(causa|causas|motivo|motivos|principal|principais|assunto|"
            r"assuntos|tipo de reclama|reclama)\b",
            re.IGNORECASE,
        ),
        ("ce-reclamacoes-totais-assuntos", "ce-reclamacoes-totais-causas"),
    ),
    (
        re.compile(
            r"\b(refatur\w*|maior taxa|mais refatur\w*|taxa de refatur\w*)\b",
            re.IGNORECASE,
        ),
        ("ce-reclamacoes-totais-refaturamento",),
    ),
    (
        re.compile(
            r"\b(mensal|mês|meses|tempo|evolu|série|serie|repete|repetem|"
            r"ao longo|tendência|tendencia|pico)\b",
            re.IGNORECASE,
        ),
        ("ce-reclamacoes-totais-evolucao",),
    ),
    (
        re.compile(r"\b(grupo|tarifári|tarifario|\bgb\b|\bga\b)\b", re.IGNORECASE),
        ("ce-reclamacoes-totais-grupo",),
    ),
    (
        re.compile(
            r"\b(quantas|total|totais|volume|visão geral|visao geral|resumo)\b",
            re.IGNORECASE,
        ),
        ("ce-reclamacoes-totais-overview",),
    ),
    (
        re.compile(
            r"\b(instala\w*|\buc\b|ucs|cliente|clientes|consumidor|consumidores|"
            r"medidor|quem .* mais reclam\w*|qual .* mais reclam\w*)\b",
            re.IGNORECASE,
        ),
        ("ce-top-instalacoes",),
    ),
    (
        re.compile(
            r"(\b(janeiro|fevereiro|março|marco|abril|maio|junho|julho|agosto|"
            r"setembro|outubro|novembro|dezembro)\b|\b20(25|26)-\d{2}\b)",
            re.IGNORECASE,
        ),
        (
            "ce-reclamacoes-totais-mensal-assuntos",
            "ce-reclamacoes-totais-mensal-causas",
        ),
    ),
)


# Boosts dedicados à região SP (universo N1 erro_leitura).
_SP_BOOSTS: tuple[tuple[re.Pattern[str], tuple[str, ...]], ...] = (
    (
        re.compile(
            r"\b(digita(?:ç|c|cao|ção|do|da|r|ndo|gem)\w*)\b.*"
            r"\b(fatura\w*|valor(?:es)?|medidor(?:es)?)\b|"
            r"\b(fatura\w*|valor(?:es)?|medidor(?:es)?)\b.*"
            r"\b(digita(?:ç|c|cao|ção|do|da|r|ndo|gem)\w*)\b",
            re.IGNORECASE,
        ),
        ("sp-digitacao-fatura-medidor", "sp-tipos-medidor-digitacao", "instalacoes-digitacao"),
    ),
    (
        re.compile(
            r"\b(fatura\w*)\b.*\b(alta\w*|maior(?:es)?|valor(?:es)?|instala\w*|data)\b|"
            r"\b(alta\w*|maior(?:es)?|valor(?:es)?|instala\w*|data)\b.*\b(fatura\w*)\b",
            re.IGNORECASE,
        ),
        ("sp-faturas-altas", "sp-fatura-medidor", "sp-perfil-assunto-lider"),
    ),
    (
        re.compile(
            r"\b(fatura\w*)\b.*\b(medidor(?:es)?|digital|analógic\w*|analogic\w*|ciclom\w*)\b|"
            r"\b(medidor(?:es)?|digital|analógic\w*|analogic\w*|ciclom\w*)\b.*\b(fatura\w*)\b",
            re.IGNORECASE,
        ),
        ("sp-fatura-medidor", "sp-tipos-medidor", "sp-causas-por-tipo-medidor"),
    ),
    (
        re.compile(
            r"\b(medidor(?:es)?)\b.*\b(problema\w*|d[aã]o problema|tipo de reclama\w*)\b|"
            r"\b(problema\w*|d[aã]o problema|tipo de reclama\w*)\b.*\b(medidor(?:es)?)\b",
            re.IGNORECASE,
        ),
        ("sp-medidores-problema-reclamacao", "sp-causas-por-tipo-medidor", "sp-tipos-medidor"),
    ),
    (
        re.compile(
            r"\b(tempo|demor\w*|soluc\w*|resolver|resolução|resolucao)\b.*"
            r"\b(reclama\w*|fatura\w*)\b|"
            r"\b(reclama\w*|fatura\w*)\b.*\b(tempo|demor\w*|soluc\w*|resolver|resolução|resolucao)\b",
            re.IGNORECASE,
        ),
        ("sp-fatura-medidor", "sp-perfil-assunto-lider", "data-quality-notes"),
    ),
    (
        re.compile(
            r"\b(motivo|motivos|causa|causas|assunto|assuntos)\b.*"
            r"\b(medidor(?:es)?|digital|analógic\w*|analogic\w*|ciclom\w*)\b|"
            r"\b(medidor(?:es)?|digital|analógic\w*|analogic\w*|ciclom\w*)\b.*"
            r"\b(motivo|motivos|causa|causas|assunto|assuntos)\b",
            re.IGNORECASE,
        ),
        ("sp-causas-por-tipo-medidor",),
    ),
    (
        re.compile(
            r"\b(assunto|assuntos|causa|causas|motivo|motivos|principal|principais|"
            r"tipo de reclama|reclama)\b",
            re.IGNORECASE,
        ),
        ("sp-n1-assuntos", "sp-n1-causas"),
    ),
    (
        re.compile(
            r"\b(mensal|mês|meses|tempo|evolu|série|serie|repete|repetem|"
            r"ao longo|tendência|tendencia|pico)\b",
            re.IGNORECASE,
        ),
        ("sp-n1-mensal",),
    ),
    (
        re.compile(r"\b(grupo|tarifári|tarifario|\bgb\b|\bga\b)\b", re.IGNORECASE),
        ("sp-n1-grupo",),
    ),
    (
        re.compile(
            r"\b(quantas|quantos|total|totais|volume|visão geral|visao geral|resumo|tickets?)\b",
            re.IGNORECASE,
        ),
        ("sp-n1-overview",),
    ),
    (
        re.compile(
            r"\b(tipos?\s+de\s+medidor(?:es)?|medidores?)\b.*\b(digita\w*)\b|"
            r"\b(digita\w*)\b.*\b(tipos?\s+de\s+medidor(?:es)?|medidores?)\b",
            re.IGNORECASE,
        ),
        ("sp-tipos-medidor-digitacao",),
    ),
    (
        re.compile(
            r"\b(tipos?\s+de\s+medidor(?:es)?|medidores?\s+existentes)\b",
            re.IGNORECASE,
        ),
        ("sp-tipos-medidor",),
    ),
    (
        re.compile(
            r"\b(instala\w*|\buc\b|ucs|cliente|clientes|consumidor|consumidores|medidor)\b",
            re.IGNORECASE,
        ),
        ("sp-n1-top-instalacoes", "sp-tipos-medidor"),
    ),
    (
        re.compile(
            r"\b(causa[ -]?raiz).*\b(observa\w*|texto|devolutiva)\b|"
            r"\b(observa\w*|texto|devolutiva).*\b(causa[ -]?raiz)\b",
            re.IGNORECASE,
        ),
        ("sp-causa-observacoes",),
    ),
    (
        re.compile(
            r"\b(perfil|tipo de medidor|medidor|fatura reclamada|data da fatura|"
            r"valor médio da fatura|valor medio da fatura|emissão|emissao|vencimento|"
            r"tempo entre)\b",
            re.IGNORECASE,
        ),
        ("sp-perfil-assunto-lider",),
    ),
)


# Cluster-level boosts: rotulagem do CSV `erro_leitura_clusterizado` (SP).
# Entram quando a query menciona fatura/medidor/leitura — promovem cards
# `descricoes-cluster-*` (sumário) e exemplos reais para grounding detalhado.
_DESCRICOES_BOOST_RULES: tuple[tuple[re.Pattern[str], tuple[str, ...]], ...] = (
    (
        re.compile(
            r"\b(medidor(?:es)?|f[ií]sico|troca\s+do?\s+medidor|defeito\s+(?:no|do)\s+medidor)\b",
            re.IGNORECASE,
        ),
        (
            "descricoes-cluster-problemas-no-medidor-f-sico",
            "descricoes-cluster-diverg-ncia-cliente-vs-sistema-problemas-no-medidor-f-sico",
        ),
    ),
    (
        re.compile(
            r"\b(divergencia|diverg[êe]ncia|leitura\s+(?:errad|incorret)\w*|sistema\s+vs)\b",
            re.IGNORECASE,
        ),
        (
            "descricoes-cluster-diverg-ncia-cliente-vs-sistema",
            "descricoes-cluster-diverg-ncia-cliente-vs-sistema-varia-o-contesta-o-de-valor",
        ),
    ),
    (
        re.compile(
            r"\b(varia[çc][ãa]o|contesta[çc][ãa]o|valor\s+alto|valor\s+da\s+fatura|fatura\s+alta)\b",
            re.IGNORECASE,
        ),
        (
            "descricoes-cluster-varia-o-contesta-o-de-valor",
            "descricoes-cluster-diverg-ncia-cliente-vs-sistema-varia-o-contesta-o-de-valor",
        ),
    ),
    (
        re.compile(
            r"\b(invers[ãa]o|invertid\w+|erro\s+de\s+digita[çc][ãa]o|digita[çc][ãa]o)\b",
            re.IGNORECASE,
        ),
        (
            "descricoes-cluster-invers-o-ou-erro-de-digita-o",
            "descricoes-cluster-diverg-ncia-cliente-vs-sistema-invers-o-ou-erro-de-digita-o-varia-o-contesta-o-de-valor",
        ),
    ),
    (
        re.compile(
            r"\b(m[ée]dia|estimativa|leitura\s+por\s+m[ée]dia)\b",
            re.IGNORECASE,
        ),
        ("descricoes-cluster-m-dia-ou-estimativa",),
    ),
    (
        re.compile(
            r"\b(impedimento\s+de\s+acesso|sem\s+acesso\s+ao\s+medidor|port[ãa]o\s+fechado)\b",
            re.IGNORECASE,
        ),
        ("descricoes-cluster-impedimento-de-acesso",),
    ),
    (
        re.compile(
            r"\b(fatura\w*|leitura\w*|consumo\w*)\b",
            re.IGNORECASE,
        ),
        (
            "descricoes-cluster-diverg-ncia-cliente-vs-sistema-varia-o-contesta-o-de-valor",
            "descricoes-cluster-diverg-ncia-cliente-vs-sistema",
            "descricoes-cluster-varia-o-contesta-o-de-valor",
        ),
    ),
)


def _is_fatura_medidor_query(question: str) -> bool:
    """Heurística rápida: query menciona fatura, medidor, leitura, valor, consumo."""
    return bool(
        re.search(
            r"\b(fatura\w*|medidor(?:es)?|leitura\w*|consumo\w*|valor\s+da\s+fatura|"
            r"divergencia|diverg[êe]ncia|digita[çc][ãa]o|m[ée]dia|estimativa)\b",
            question,
            re.IGNORECASE,
        )
    )


def detect_card_boosts(
    question: str,
    *,
    region: Literal["CE", "SP", "CE+SP"] | None = None,
) -> list[str]:
    """Retorna anchors canônicos a forçar em top-N, respeitando ordem de prioridade.

    Quando a região detectada é CE, aplica boost CE-total PRIMEIRO para
    priorizar o universo completo de 167k reclamações sobre o subset rotulado.
    """
    seen: dict[str, None] = {}
    if region == "CE":
        for pattern, anchors in _CE_TOTAL_BOOSTS:
            if pattern.search(question):
                for anchor in anchors:
                    seen.setdefault(anchor, None)
    if region == "SP":
        for pattern, anchors in _SP_BOOSTS:
            if pattern.search(question):
                for anchor in anchors:
                    seen.setdefault(anchor, None)
    for pattern, anchors in _CARD_BOOST_RULES:
        if pattern.search(question):
            for anchor in anchors:
                seen.setdefault(anchor, None)
    # Cluster boosts (SP): só fazem sentido quando região permite SP.
    if region in {"SP", "CE+SP", None}:
        for pattern, anchors in _DESCRICOES_BOOST_RULES:
            if pattern.search(question):
                for anchor in anchors:
                    seen.setdefault(anchor, None)
    return list(seen.keys())


def is_individual_client_query(question: str) -> bool:
    """Queries sobre cliente/UC individual: recusar cedo com orientação agregada."""
    return bool(_INDIVIDUAL_CLIENT_RE.search(question))


SP_PROFILE_SCOPE_MESSAGE = (
    "O perfil detalhado com **tipo de medidor** e **faturas reclamadas** está "
    "disponível somente para **SP** nesta versão. Para CE, consigo responder "
    "com métricas agregadas de assuntos, causas, sazonalidade e reincidência."
)


def is_profile_detail_query(question: str) -> bool:
    """Detecta perguntas de perfil detalhado cliente/fatura/medidor."""
    return bool(_PROFILE_DETAIL_RE.search(question))


@dataclass(frozen=True, slots=True)
class RagResponse:
    text: str
    passages: list[Passage]
    intent: str
    prompt_tokens: int
    completion_tokens: int
    latency_ms: float
    blocked_reason: str | None = None
    region_detected: Literal["CE", "SP", "CE+SP"] | None = None
    out_of_regional_scope: bool = False
    cache_hit: bool = False
    cache_seed_id: str | None = None
    question_hash: str | None = None


@dataclass(frozen=True, slots=True)
class RagStreamEvent:
    event: str
    payload: dict[str, Any]


@dataclass(slots=True)
class _Timer:
    started: float = field(default_factory=time.perf_counter)
    first_token_ms: float = 0.0

    def mark_first_token(self) -> None:
        if self.first_token_ms == 0.0:
            self.first_token_ms = (time.perf_counter() - self.started) * 1000.0

    def total_ms(self) -> float:
        return (time.perf_counter() - self.started) * 1000.0


def classify_intent(question: str) -> str:
    q = question.strip().lower()
    if _GREETING_RE.match(q):
        return "saudacao"
    if any(t in q for t in ("obrigad", "valeu", "tchau", "até logo")):
        return "cortesia"
    if any(t in q for t in ("sprint", "entregável", "roadmap")):
        return "sprint"
    if any(t in q for t in ("modelo", "classific", "predict", "acurácia")):
        return "ml"
    if any(t in q for t in ("dashboard", "aba", "gráfico", "filtro", "streamlit")):
        return "dashboard_howto"
    if any(
        t in q
        for t in (
            "por que",
            "porque",
            "causa",
            "explique",
            "análise",
            "analise",
            "quantos",
            "quantas",
            "volume",
            "taxa",
            "percentual",
            "mensal",
            "total",
            "reclama",
            "problema",
            "problemas",
            "erro de leitura",
            "digita",
            "instala",
            "uc",
            "medidor",
            "tipos de medidor",
            "tipo de medidor",
            "compare",
            "compar",
            "resumo",
            "dados",
            "taxonomia",
        )
    ):
        return "analise_dados"
    if any(t in q for t in ("como rodar", "como executar", "como instalar", "comando")):
        return "dev"
    return "glossario"


def detect_regional_scope(question: str) -> Literal["CE", "SP", "CE+SP"] | None:
    ce = bool(_CE_RE.search(question))
    sp = bool(_SP_RE.search(question))
    if ce and sp:
        return "CE+SP"
    if ce:
        return "CE"
    if sp:
        return "SP"
    return None


def greeting_response(context_hint: str | None = None) -> str:
    hour = datetime.now(UTC).astimezone().hour
    if 5 <= hour < 12:
        saud = "Bom dia!"
    elif 12 <= hour < 18:
        saud = "Boa tarde!"
    else:
        saud = "Boa noite!"
    base = (
        f"{saud} Sou o Assistente ENEL. Posso responder sobre arquitetura do lakehouse, "
        "regras de negócio (ACF/ASF, GD, refaturamento), modelos de ML, dashboards e "
        "sprints do projeto."
    )
    if context_hint:
        return (
            f"{base} Vi que você estava em **{context_hint}** — quer um resumo "
            "dessa área ou tem alguma pergunta específica?"
        )
    return f"{base} Sobre o que quer conversar?"


class RagOrchestrator:
    """Pipeline completa: valida → classifica → recupera → prompta → gera → cita."""

    def __init__(
        self,
        config: RagConfig,
        *,
        retriever: HybridRetriever | None = None,
        provider: LLMProvider | None = None,
    ) -> None:
        self.config = config
        self.retriever = retriever or HybridRetriever(config)
        self.provider = provider or build_provider(config)
        self.positive_cache = PositiveCache()
        self.active_boosts = self._load_active_boosts()

    def _load_active_boosts(self) -> dict[str, float]:
        path = Path("data/rag_train/active_boosts.json")
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def _history_summary_enabled(self) -> bool:
        raw = os.getenv("RAG_HISTORY_SUMMARY_ENABLED", "1").strip().lower()
        return raw in {"1", "true", "yes", "on"}

    def _history_summary_max_turns(self) -> int:
        raw = os.getenv("RAG_HISTORY_SUMMARY_MAX_TURNS", "8").strip()
        try:
            return max(4, int(raw))
        except ValueError:
            return 8

    def _build_history_summary(self, history: list[dict[str, str]] | None) -> str | None:
        if not self._history_summary_enabled():
            return None
        turns = [
            {
                "role": str(turn.get("role", "")),
                "content": str(turn.get("content", "")).strip(),
            }
            for turn in (history or [])
            if str(turn.get("role", "")) in {"user", "assistant"}
            and str(turn.get("content", "")).strip()
        ]
        if len(turns) <= self._history_summary_max_turns():
            return None
        # Resumo cobre o histórico antigo, preservando os 4 últimos turnos íntegros.
        older = turns[:-4]
        if not older:
            return None
        text = ""
        try:
            provider_name = str(getattr(self.provider, "name", "")).lower()
            if provider_name not in {"", "stub"}:
                summary_prompt = build_summarize_history_prompt(older)
                response = self.provider.complete(
                    summary_prompt,
                    max_tokens=96,
                    temperature=0.0,
                    top_p=1.0,
                )
                text = sanitize_output(response.text).strip()
        except Exception:
            text = ""
        if not text:
            text = self._local_history_summary(older)
        if not text:
            return None
        return text[:_SUMMARY_MAX_CHARS].strip()

    @staticmethod
    def _local_history_summary(history: list[dict[str, str]]) -> str:
        user_signals: list[str] = []
        assistant_signals: list[str] = []
        for turn in history:
            content = str(turn.get("content", "")).replace("\n", " ").strip()
            if not content:
                continue
            snippet = content[:120]
            if turn.get("role") == "user":
                user_signals.append(snippet)
            elif turn.get("role") == "assistant":
                assistant_signals.append(snippet)
        parts: list[str] = []
        if user_signals:
            parts.append(f"Usuário já perguntou sobre: {' | '.join(user_signals[-3:])}.")
        if assistant_signals:
            parts.append(
                f"Assistente já respondeu com foco em: {' | '.join(assistant_signals[-3:])}."
            )
        return " ".join(parts).strip()

    def answer(
        self,
        question: str,
        *,
        history: list[dict[str, str]] | None = None,
        context_hint: str | None = None,
        dataset_version: str | None = None,
        golden_case_id: str | None = None,
    ) -> RagResponse:
        timer = _Timer()
        check = check_input(question)
        q_hash = hash_question(check.sanitized if check.allowed else question)
        if not check.allowed:
            return RagResponse(
                text=check.reason or "Pergunta inválida.",
                passages=[],
                intent="blocked",
                prompt_tokens=0,
                completion_tokens=0,
                latency_ms=timer.total_ms(),
                blocked_reason=check.reason,
                question_hash=q_hash,
            )

        if is_out_of_regional_scope(check.sanitized):
            self._record(
                question=check.sanitized,
                intent="out_of_regional_scope",
                passages=[],
                prompt_tokens=0,
                completion_tokens=0,
                first_token_ms=timer.first_token_ms or timer.total_ms(),
                total_ms=timer.total_ms(),
                region_detected=None,
                out_of_regional_scope=True,
                golden_case_id=golden_case_id,
                cache_hit=True,
                extra={"seed_id": "regional-scope-refusal"},
            )
            return RagResponse(
                text=OUT_OF_REGIONAL_SCOPE_MESSAGE,
                passages=[],
                intent="out_of_regional_scope",
                prompt_tokens=0,
                completion_tokens=0,
                latency_ms=timer.total_ms(),
                region_detected=None,
                out_of_regional_scope=True,
                cache_hit=True,
                cache_seed_id="regional-scope-refusal",
                question_hash=q_hash,
            )

        # MVP: perguntas sobre instalação/UC agora são roteadas para cards
        # `*-top-instalacoes` (via boosts). A recusa individual foi removida —
        # `INDIVIDUAL_CLIENT_MESSAGE` permanece disponível para rollback futuro.
        intent = classify_intent(check.sanitized)
        region = detect_regional_scope(check.sanitized)
        profile_detail = is_profile_detail_query(check.sanitized)
        if profile_detail and region in {"CE", "CE+SP"}:
            self._record(
                question=check.sanitized,
                intent="profile_scope_limited",
                passages=[],
                prompt_tokens=0,
                completion_tokens=len(SP_PROFILE_SCOPE_MESSAGE) // 4,
                first_token_ms=timer.first_token_ms or timer.total_ms(),
                total_ms=timer.total_ms(),
                region_detected=region,
                out_of_regional_scope=False,
                golden_case_id=golden_case_id,
            )
            return RagResponse(
                text=SP_PROFILE_SCOPE_MESSAGE,
                passages=[],
                intent="profile_scope_limited",
                prompt_tokens=0,
                completion_tokens=len(SP_PROFILE_SCOPE_MESSAGE) // 4,
                latency_ms=timer.total_ms(),
                region_detected=region,
                out_of_regional_scope=False,
            )
        if profile_detail and region is None:
            region = "SP"
        elif region is None and intent in ANALYTICAL_INTENTS:
            region = "CE+SP"

        # 1. Positive Cache Lookup (Sprint 26)
        cached_positive = self.positive_cache.lookup(check.sanitized)
        if cached_positive:
            total_ms = timer.total_ms()
            return RagResponse(
                text=cached_positive["answer"],
                passages=[
                    Passage(
                        chunk_id="cache",
                        text=cached_positive["answer"],
                        source_path="cache",
                        section="cache",
                        doc_type="cache",
                        sprint_id="26",
                        anchor="cache",
                        score=1.0,
                    )
                ],
                intent="positive_cache",
                prompt_tokens=0,
                completion_tokens=len(cached_positive["answer"]) // 4,
                latency_ms=total_ms,
                cache_hit=True,
                question_hash=q_hash,
            )

        cached = self._resolve_cached_answer(
            check.sanitized,
            intent=intent,
            region=region,
            dataset_version=dataset_version,
        )
        if cached is not None:
            total_ms = timer.total_ms()
            self._record(
                question=check.sanitized,
                intent=cached.intent,
                passages=cached.passages,
                prompt_tokens=0,
                completion_tokens=len(cached.text) // 4,
                first_token_ms=timer.first_token_ms or total_ms,
                total_ms=total_ms,
                region_detected=cached.region_detected,
                out_of_regional_scope=cached.intent == "out_of_regional_scope",
                golden_case_id=golden_case_id,
                cache_hit=True,
                extra={
                    "seed_id": cached.seed_id,
                    "seed_version": cached.seed_version,
                    "cache_score": cached.score,
                    "answer_mode": cached.answer_mode,
                },
            )
            return RagResponse(
                text=cached.text,
                passages=cached.passages,
                intent=cached.intent,
                prompt_tokens=0,
                completion_tokens=len(cached.text) // 4,
                latency_ms=total_ms,
                region_detected=cached.region_detected,
                out_of_regional_scope=cached.intent == "out_of_regional_scope",
                cache_hit=True,
                cache_seed_id=cached.seed_id,
                question_hash=q_hash,
            )

        if intent in {"saudacao", "cortesia"}:
            text = greeting_response(context_hint)
            self._record(
                question=check.sanitized,
                intent=intent,
                passages=[],
                prompt_tokens=0,
                completion_tokens=len(text) // 4,
                first_token_ms=timer.first_token_ms or timer.total_ms(),
                total_ms=timer.total_ms(),
                region_detected=region,
                out_of_regional_scope=False,
                golden_case_id=golden_case_id,
            )
            return RagResponse(
                text=text,
                passages=[],
                intent=intent,
                prompt_tokens=0,
                completion_tokens=len(text) // 4,
                latency_ms=timer.total_ms(),
                region_detected=region,
                question_hash=q_hash,
            )

        doc_types = route_doc_types(check.sanitized)
        try:
            passages = self._top_passages(
                check.sanitized,
                doc_types=doc_types,
                dataset_version=dataset_version,
                region=region,
            )
        except (FileNotFoundError, RuntimeError) as exc:
            return RagResponse(
                text=(
                    "Índice RAG não disponível. Rode: "
                    "`python scripts/build_rag_corpus.py --rebuild` para indexar os docs.\n\n"
                    f"_Detalhe técnico_: {exc}"
                ),
                passages=[],
                intent="no_index",
                prompt_tokens=0,
                completion_tokens=0,
                latency_ms=timer.total_ms(),
                blocked_reason="no_index",
                region_detected=region,
                question_hash=q_hash,
            )

        if is_out_of_scope(passages, self.config.similarity_threshold):
            return RagResponse(
                text=OUT_OF_SCOPE_MESSAGE,
                passages=passages,
                intent="out_of_scope",
                prompt_tokens=0,
                completion_tokens=0,
                latency_ms=timer.total_ms(),
                region_detected=region,
                question_hash=q_hash,
            )

        history_summary = self._build_history_summary(history)
        passages = self._enforce_budget(
            passages,
            question=check.sanitized,
            history=history,
            history_summary=history_summary,
        )
        direct_text = self._direct_answer_from_data(
            check.sanitized,
            passages=passages,
            intent=intent,
        )
        if direct_text is not None:
            self._record(
                question=check.sanitized,
                intent=intent,
                passages=passages,
                prompt_tokens=0,
                completion_tokens=len(direct_text) // 4,
                first_token_ms=timer.first_token_ms or timer.total_ms(),
                total_ms=timer.total_ms(),
                region_detected=region,
                out_of_regional_scope=False,
                golden_case_id=golden_case_id,
            )
            return RagResponse(
                text=direct_text,
                passages=passages,
                intent=intent,
                prompt_tokens=0,
                completion_tokens=len(direct_text) // 4,
                latency_ms=timer.total_ms(),
                region_detected=region,
                question_hash=q_hash,
            )
        messages = build_messages(
            question=check.sanitized,
            passages=passages,
            history=history,
            history_summary=history_summary,
        )

        tools = [
            {
                "type": "function",
                "function": {
                    "name": "get_metrics_summary",
                    "description": "Obtém resumo de métricas do DataStore real.",
                    "parameters": {"type": "object", "properties": {}}
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_installation_details",
                    "description": (
                        "Obtém dados detalhados de faturas, medidores e observações "
                        "de uma instalação específica."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "instalacao_id": {
                                "type": "string",
                                "description": "ID ou número da instalação (UC)."
                            }
                        },
                        "required": ["instalacao_id"]
                    }
                }
            }
        ]

        resp = self.provider.complete(
            messages,
            max_tokens=self._answer_budget(
                question=check.sanitized,
                history=history,
                history_summary=history_summary,
            ),
            temperature=self.config.temperature,
            top_p=self.config.top_p,
            tools=tools,
        )
        timer.mark_first_token()
        text = sanitize_output(resp.text).strip()
        text = self._guardrail_not_found(text, passages=passages, intent=intent)
        text = self._append_deterministic_citations(text, passages=passages, intent=intent)

        self._record(
            question=check.sanitized,
            intent=intent,
            passages=passages,
            prompt_tokens=resp.prompt_tokens,
            completion_tokens=len(text) // 4,
            first_token_ms=timer.first_token_ms,
            total_ms=timer.total_ms(),
            region_detected=region,
            out_of_regional_scope=False,
            golden_case_id=golden_case_id,
        )
        return RagResponse(
            text=text,
            passages=passages,
            intent=intent,
            prompt_tokens=resp.prompt_tokens,
            completion_tokens=resp.completion_tokens,
            latency_ms=timer.total_ms(),
            region_detected=region,
            question_hash=q_hash,
        )

    def stream_events(
        self,
        question: str,
        *,
        history: list[dict[str, str]] | None = None,
        context_hint: str | None = None,
        dataset_version: str | None = None,
    ) -> Iterator[RagStreamEvent]:
        timer = _Timer()
        check = check_input(question)
        q_hash = hash_question(check.sanitized if check.allowed else question)
        if not check.allowed:
            text = check.reason or "Pergunta inválida."
            yield RagStreamEvent("token", {"text": text})
            yield self._done_event(q_hash, timer, cache_hit=False)
            return
        yield RagStreamEvent("stage", {"key": "validate", "status": "done"})

        if is_out_of_regional_scope(check.sanitized):
            yield RagStreamEvent("token", {"text": OUT_OF_REGIONAL_SCOPE_MESSAGE})
            self._record(
                question=check.sanitized,
                intent="out_of_regional_scope",
                passages=[],
                prompt_tokens=0,
                completion_tokens=len(OUT_OF_REGIONAL_SCOPE_MESSAGE) // 4,
                first_token_ms=timer.total_ms(),
                total_ms=timer.total_ms(),
                region_detected=None,
                out_of_regional_scope=True,
                golden_case_id=None,
                cache_hit=True,
                extra={"seed_id": "regional-scope-refusal"},
            )
            yield self._done_event(
                q_hash,
                timer,
                cache_hit=True,
                seed_id="regional-scope-refusal",
            )
            return

        intent = classify_intent(check.sanitized)
        region = detect_regional_scope(check.sanitized)
        yield RagStreamEvent(
            "stage",
            {
                "key": "route",
                "status": "done",
                "label": f"Rota: {intent} · {region or 'CE+SP'}",
            },
        )
        profile_detail = is_profile_detail_query(check.sanitized)
        if profile_detail and region in {"CE", "CE+SP"}:
            yield RagStreamEvent("token", {"text": SP_PROFILE_SCOPE_MESSAGE})
            yield self._done_event(q_hash, timer, cache_hit=False)
            return
        if profile_detail and region is None:
            region = "SP"
        elif region is None and intent in ANALYTICAL_INTENTS:
            region = "CE+SP"

        # 1. Positive Cache Lookup (Sprint 26)
        cached_positive = self.positive_cache.lookup(check.sanitized)
        if cached_positive:
            yield RagStreamEvent(
                "stage",
                {"key": "cache", "status": "done", "label": "Resposta cacheada (Positiva)"},
            )
            yield RagStreamEvent("token", {"text": cached_positive["answer"]})
            total_ms = timer.total_ms()
            yield self._done_event(
                q_hash,
                timer,
                cache_hit=True,
                intent="positive_cache",
                passages=[
                    Passage(
                        chunk_id="cache",
                        text=cached_positive["answer"],
                        source_path="cache",
                        section="cache",
                        doc_type="cache",
                        sprint_id="26",
                        anchor="cache",
                        score=1.0,
                    )
                ],
            )
            return

        cached = self._resolve_cached_answer(
            check.sanitized,
            intent=intent,
            region=region,
            dataset_version=dataset_version,
        )
        if cached is not None:
            yield RagStreamEvent(
                "stage",
                {"key": "cache", "status": "done", "label": "Resposta cacheada"},
            )
            yield RagStreamEvent("token", {"text": cached.text})
            total_ms = timer.total_ms()
            self._record(
                question=check.sanitized,
                intent=cached.intent,
                passages=cached.passages,
                prompt_tokens=0,
                completion_tokens=len(cached.text) // 4,
                first_token_ms=timer.first_token_ms or total_ms,
                total_ms=total_ms,
                region_detected=cached.region_detected,
                out_of_regional_scope=cached.intent == "out_of_regional_scope",
                golden_case_id=None,
                cache_hit=True,
                extra={
                    "seed_id": cached.seed_id,
                    "seed_version": cached.seed_version,
                    "cache_score": cached.score,
                    "answer_mode": cached.answer_mode,
                },
            )
            yield self._done_event(
                q_hash,
                timer,
                cache_hit=True,
                seed_id=cached.seed_id,
                intent=cached.intent,
                passages=cached.passages,
            )
            return

        captured: dict[str, Any] = {"intent": intent, "passages": []}
        yield RagStreamEvent(
            "stage",
            {
                "key": "retrieve",
                "status": "active",
                "label": "Consultando silver, data cards e documentos",
            },
        )

        def capture_passages(passages: list[Passage], resolved_intent: str) -> None:
            captured["intent"] = resolved_intent
            captured["passages"] = passages

        for token in self.stream_answer(
            check.sanitized,
            history=history,
            context_hint=context_hint,
            dataset_version=dataset_version,
            on_passages=capture_passages,
        ):
            if not captured.get("first_token"):
                captured["first_token"] = True
                yield RagStreamEvent(
                    "stage",
                    {
                        "key": "generate",
                        "status": "active",
                        "label": "Gerando resposta baseada nas fontes",
                    },
                )
            yield RagStreamEvent("token", {"text": token})
        yield RagStreamEvent("stage", {"key": "generate", "status": "done"})
        yield self._done_event(
            q_hash,
            timer,
            cache_hit=False,
            intent=str(captured.get("intent") or intent),
            passages=list(captured.get("passages") or []),
        )

    def stream_answer(
        self,
        question: str,
        *,
        history: list[dict[str, str]] | None = None,
        context_hint: str | None = None,
        dataset_version: str | None = None,
        on_passages: Callable[[list[Passage], str], None] | None = None,
    ) -> Iterator[str]:
        """Versão streaming: emite chunks de texto conforme chegam.

        Para saudação/out-of-scope retorna texto completo em um único yield.
        """
        timer = _Timer()
        check = check_input(question)
        if not check.allowed:
            yield check.reason or "Pergunta inválida."
            return

        if is_out_of_regional_scope(check.sanitized):
            yield OUT_OF_REGIONAL_SCOPE_MESSAGE
            return

        intent = classify_intent(check.sanitized)
        region = detect_regional_scope(check.sanitized)
        profile_detail = is_profile_detail_query(check.sanitized)
        if profile_detail and region in {"CE", "CE+SP"}:
            yield SP_PROFILE_SCOPE_MESSAGE
            return
        if profile_detail and region is None:
            region = "SP"
        elif region is None and intent in ANALYTICAL_INTENTS:
            region = "CE+SP"
        if intent in {"saudacao", "cortesia"}:
            yield greeting_response(context_hint)
            return

        try:
            passages = self._top_passages(
                check.sanitized,
                doc_types=route_doc_types(check.sanitized),
                dataset_version=dataset_version,
                region=region,
            )
        except (FileNotFoundError, RuntimeError) as exc:
            yield (
                "Índice RAG não disponível. Rode: "
                "`python scripts/build_rag_corpus.py --rebuild`.\n\n"
                f"_{exc}_"
            )
            return

        # Boosts determinísticos (via _top_passages) injetam passages com
        # score sintético 0.99, então is_out_of_scope só bloqueia quando não
        # houve boost E a semântica também falhou.
        if is_out_of_scope(passages, self.config.similarity_threshold):
            yield OUT_OF_SCOPE_MESSAGE
            return

        history_summary = self._build_history_summary(history)
        passages = self._enforce_budget(
            passages,
            question=check.sanitized,
            history=history,
            history_summary=history_summary,
        )
        if on_passages is not None:
            on_passages(passages, intent)
        direct_text = self._direct_answer_from_data(
            check.sanitized,
            passages=passages,
            intent=intent,
        )
        if direct_text is not None:
            timer.mark_first_token()
            yield direct_text
            self._record(
                question=check.sanitized,
                intent=intent,
                passages=passages,
                prompt_tokens=0,
                completion_tokens=len(direct_text) // 4,
                first_token_ms=timer.first_token_ms,
                total_ms=timer.total_ms(),
                region_detected=region,
                out_of_regional_scope=False,
                golden_case_id=None,
            )
            return
        messages = build_messages(
            question=check.sanitized,
            passages=passages,
            history=history,
            history_summary=history_summary,
        )

        # Sprint 20: Integração de Function Calling
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "get_metrics_summary",
                    "description": "Obtém resumo de métricas do DataStore real.",
                    "parameters": {"type": "object", "properties": {}}
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_installation_details",
                    "description": (
                        "Obtém dados detalhados de faturas, medidores e observações "
                        "de uma instalação específica."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "instalacao_id": {
                                "type": "string",
                                "description": "ID ou número da instalação (UC)."
                            }
                        },
                        "required": ["instalacao_id"]
                    }
                }
            }
        ]

        acc_text = []
        for chunk in self.provider.stream(
            messages,
            max_tokens=self._answer_budget(
                question=check.sanitized,
                history=history,
                history_summary=history_summary,
            ),
            temperature=self.config.temperature,
            top_p=self.config.top_p,
            tools=tools,
        ):
            timer.mark_first_token()
            acc_text.append(chunk)
            yield chunk
        joined = "".join(acc_text)
        sanitized = sanitize_output(joined).strip()
        final_text = self._guardrail_not_found(sanitized, passages=passages, intent=intent)
        final_text = self._append_deterministic_citations(
            final_text,
            passages=passages,
            intent=intent,
        )
        if sanitized != joined.strip():
            # PII detectada pós-geração: emite correção clara (não silencia).
            yield "\n\n_[saída sanitizada — PII removida]_"
        if final_text != sanitized:
            suffix = (
                final_text[len(sanitized):]
                if final_text.startswith(sanitized)
                else f"\n\n{format_citations(passages)}"
            )
            if suffix:
                yield suffix

        self._record(
            question=check.sanitized,
            intent=intent,
            passages=passages,
            prompt_tokens=0,
            completion_tokens=len(final_text) // 4,
            first_token_ms=timer.first_token_ms,
            total_ms=timer.total_ms(),
            region_detected=region,
            out_of_regional_scope=False,
            golden_case_id=None,
        )

    def _resolve_cached_answer(
        self,
        question: str,
        *,
        intent: str,
        region: Literal["CE", "SP", "CE+SP"] | None,
        dataset_version: str | None,
    ) -> CachedAnswer | None:
        def load_passages(anchors: list[str]) -> list[Passage]:
            return self.retriever.get_by_anchors(anchors, dataset_version=dataset_version)

        try:
            return resolve_known_answer(
                question,
                intent=intent,
                region=region,
                dataset_hash=dataset_version,
                passage_loader=load_passages,
            )
        except (FileNotFoundError, RuntimeError):
            return None

    def _done_event(
        self,
        question_hash: str,
        timer: _Timer,
        *,
        cache_hit: bool,
        seed_id: str | None = None,
        intent: str | None = None,
        passages: list[Passage] | None = None,
    ) -> RagStreamEvent:
        passages = passages or []
        return RagStreamEvent(
            "done",
            {
                "ok": True,
                "question_hash": question_hash,
                "cache_hit": cache_hit,
                "cache_seed_id": seed_id,
                "latency_ms": timer.total_ms(),
                "intent": intent,
                "sources": _source_payload(passages),
                "sources_count": len(passages),
                "provider": getattr(self.provider, "name", "unknown"),
                "model": getattr(self.provider, "model", "unknown"),
                "n_threads": self.config.n_threads,
                "retrieval_k": self.config.retrieval_k,
                "rerank_top_n": self.config.rerank_top_n,
                "regional_scope": self.config.regional_scope,
            },
        )

    def _top_passages(
        self,
        query: str,
        *,
        doc_types: list[str] | None,
        dataset_version: str | None,
        region: Literal["CE", "SP", "CE+SP"] | None,
    ) -> list[Passage]:
        top_n = self.config.rerank_top_n
        forced_anchors = detect_card_boosts(query, region=region)
        forced = self._forced_passages(
            forced_anchors,
            dataset_version=dataset_version,
            region=region,
        )
        if forced and self._can_answer_from_forced_data(forced):
            return forced[:top_n]

        # Primeiro passo: recuperação semântica + lexical padrão, mas pedindo
        # mais passages (2x top_n) para permitir merge com boosts sem perder
        # diversidade.
        kwargs: dict[str, Any] = {
            "top_n": top_n * 2,
            "doc_types": doc_types,
            "region": region,
        }
        semantic = self.retriever.top_passages(query, **kwargs)
        # Query decomposition: quando a pergunta tem duas etapas (entidade + métrica),
        # roda recuperações auxiliares para reforçar cards de drill-down.
        for subquery in self._decompose_query(query, region=region):
            if subquery.casefold() == query.casefold():
                continue
            extra = self.retriever.top_passages(subquery, **kwargs)
            semantic = self._merge_semantic_passages(
                semantic,
                extra,
                limit=top_n * 3,
            )

        # Segundo passo: boost determinístico — cards canônicos forçados no topo
        # quando a intenção da query é claramente identificável por keyword.
        if forced:
            forced_ids = {p.chunk_id for p in forced}
            # Mantém ordem: boosts primeiro (ordem de prioridade) — mesmo que o
            # card já tenha vindo da semântica, promove para o topo com score
            # sintético alto. Remove duplicatas dos semantic.
            merged: list[Passage] = list(forced)
            seen = set(forced_ids)
            for p in semantic:
                if p.chunk_id not in seen:
                    merged.append(p)
                    seen.add(p.chunk_id)
            return merged[:top_n]
        return semantic[:top_n]

    def _forced_passages(
        self,
        anchors: list[str],
        *,
        dataset_version: str | None,
        region: Literal["CE", "SP", "CE+SP"] | None,
    ) -> list[Passage]:
        if not anchors:
            return []
        forced = (
            self._live_data_passages(
                anchors,
                dataset_version=dataset_version,
                region=region,
            )
            if isinstance(self.retriever, HybridRetriever)
            else []
        )
        indexed_forced = self.retriever.get_by_anchors(
            anchors,
            dataset_version=dataset_version,
        )
        live_anchors = {p.anchor for p in forced}
        forced.extend(p for p in indexed_forced if p.anchor not in live_anchors)
        if region in {"CE", "SP"}:
            forced = [p for p in forced if p.region in {region, "CE+SP"}]
        ordered = {anchor: index for index, anchor in enumerate(anchors)}
        promoted = []
        for passage in forced:
            index = ordered.get(passage.anchor, len(ordered))
            base_score = max(float(passage.score), 1.25 - index * 0.01)
            
            # Aplica boost dinâmico da Sprint 26
            boost_factor = self.active_boosts.get(passage.anchor, 1.0)
            final_score = base_score * boost_factor
            
            promoted.append(replace(passage, score=final_score))
            
        promoted.sort(key=lambda passage: ordered.get(passage.anchor, 10**9))
        return promoted

    @staticmethod
    def _can_answer_from_forced_data(passages: list[Passage]) -> bool:
        return any(
            passage.doc_type == "data"
            and passage.data_source == "silver.erro_leitura_normalizado"
            for passage in passages
        )

    @staticmethod
    def _live_data_passages(
        anchors: list[str],
        *,
        dataset_version: str | None,
        region: Literal["CE", "SP", "CE+SP"] | None,
    ) -> list[Passage]:
        if not anchors:
            return []
        try:
            from src.data_plane import DataStore
            from src.data_plane.cards import build_selected_data_cards

            store = DataStore()
            chunks = build_selected_data_cards(
                store,
                anchors,
                regional_scope=region or "CE+SP",
            )
            if not chunks:
                chunks = store.cards(regional_scope=region or "CE+SP")
        except Exception:
            return []
        wanted = set(anchors)
        ordered = {anchor: index for index, anchor in enumerate(anchors)}
        passages: list[Passage] = []
        for chunk in chunks:
            if chunk.anchor not in wanted:
                continue
            score = 1.25 - (ordered.get(chunk.anchor, 0) * 0.01)
            passages.append(
                Passage(
                    chunk_id=f"live::{chunk.chunk_id}",
                    text=chunk.text,
                    source_path=chunk.source_path,
                    section=chunk.section,
                    doc_type=chunk.doc_type,
                    sprint_id=chunk.sprint_id,
                    anchor=chunk.anchor,
                    score=score,
                    dataset_version=dataset_version or chunk.dataset_version,
                    region=chunk.region,
                    scope=chunk.scope,
                    data_source=chunk.data_source,
                )
            )
        passages.sort(key=lambda passage: ordered.get(passage.anchor, 10**9))
        return passages

    @staticmethod
    def _merge_semantic_passages(
        primary: list[Passage],
        secondary: list[Passage],
        *,
        limit: int,
    ) -> list[Passage]:
        order: dict[str, int] = {
            passage.chunk_id: idx for idx, passage in enumerate(primary)
        }
        best: dict[str, Passage] = {passage.chunk_id: passage for passage in primary}
        for passage in secondary:
            previous = best.get(passage.chunk_id)
            if previous is None:
                order[passage.chunk_id] = len(order)
                best[passage.chunk_id] = passage
                continue
            if passage.score > previous.score:
                best[passage.chunk_id] = passage
        merged = sorted(
            best.values(),
            key=lambda passage: (-passage.score, order.get(passage.chunk_id, 10**9)),
        )
        return merged[: max(limit, 1)]

    @staticmethod
    def _decompose_query(
        query: str,
        *,
        region: Literal["CE", "SP", "CE+SP"] | None,
    ) -> list[str]:
        q = query.strip()
        low = q.casefold()
        out: list[str] = []
        if _METER_REASON_QUERY_RE.search(q):
            meter = ""
            if "digital" in low:
                meter = "digital"
            elif "analóg" in low or "analog" in low:
                meter = "analógico"
            elif "ciclom" in low:
                meter = "ciclométrico"
            scope = "SP" if region in {"SP", "CE+SP", None} else str(region)
            out.append(
                " ".join(
                    part
                    for part in (
                        scope,
                        "top motivos causas por tipo de medidor",
                        meter,
                        "qtd ordens percentual no tipo",
                    )
                    if part
                )
            )
        if _REFAT_EXPLANATION_RE.search(q):
            out.append(
                "CE refaturamento produtos explicabilidade assunto causa recorrencia "
                "reclamacoes totais"
            )
        return out

    def _guardrail_not_found(
        self,
        text: str,
        *,
        passages: list[Passage],
        intent: str,
    ) -> str:
        if intent not in ANALYTICAL_INTENTS:
            return text
        if not passages:
            return text
        if not _GENERIC_FALLBACK_RE.search(text):
            return text
        source = self._best_drilldown_passage(passages)
        if source is None:
            return text
        summary = self._short_answer_from_passage(source)
        citation = source.citation()
        if citation.lower() not in summary.lower():
            summary = f"{summary}\n\n{citation}"
        return summary.strip()

    @staticmethod
    def _append_deterministic_citations(
        text: str,
        *,
        passages: list[Passage],
        intent: str,
    ) -> str:
        if intent not in ANALYTICAL_INTENTS:
            return text
        cite_block = format_citations(passages)
        if not cite_block:
            return text
        if cite_block.strip() in text:
            return text
        base = text.rstrip()
        if not base:
            return cite_block.strip()
        return f"{base}\n{cite_block}"

    @staticmethod
    def _best_drilldown_passage(passages: list[Passage]) -> Passage | None:
        for passage in passages:
            if passage.anchor in _DRILLDOWN_CANONICAL_ANCHORS:
                return passage
        return passages[0] if passages else None

    @staticmethod
    def _short_answer_from_passage(passage: Passage) -> str:
        blocks = [block.strip() for block in passage.text.split("\n\n") if block.strip()]
        if not blocks:
            return "Encontrei dados relevantes no card canônico para esta pergunta."
        if blocks[0].startswith("# ") and len(blocks) > 1:
            return "\n\n".join(blocks[1:4])
        if len(blocks) == 1:
            return blocks[0]
        second = blocks[1]
        if second.startswith("**") or second.startswith("-"):
            return f"{blocks[0]}\n\n{second}"
        return blocks[0]

    def _direct_answer_from_data(
        self,
        query: str,
        *,
        passages: list[Passage],
        intent: str,
    ) -> str | None:
        if intent not in ANALYTICAL_INTENTS:
            return None
        live_data = [
            passage
            for passage in passages
            if passage.doc_type == "data"
            and passage.data_source == "silver.erro_leitura_normalizado"
            and passage.chunk_id.startswith("live::")
        ]
        if not live_data:
            return None
        source = self._best_drilldown_passage(live_data)
        if source is None:
            return None
        summary = self._short_answer_from_passage(source)
        citation = source.citation()
        if citation.lower() not in summary.lower():
            summary = f"{summary}\n\n{citation}"
        if "data-quality-notes" not in source.anchor and source.region == "SP":
            caveat = (
                "Nota de qualidade: SP está no universo N1 de erro de leitura; "
                "refaturamento resolvido pode estar subnotificado."
            )
            summary = f"{summary}\n\n{caveat}"
        return summary.strip()

    def _answer_budget(
        self,
        *,
        question: str = "",
        history: list[dict[str, str]] | None = None,
        history_summary: str | None = None,
    ) -> int:
        """Teto de tokens de resposta para SLA de ~35s em CPU (Qwen 2.5 3B Q4).

        Aproximação: ~12-14 tok/s em i7-1185G7 → 35s ≈ 400 tokens úteis.
        Respostas curtas e diretas também reforçam as regras de exatidão.
        """
        # Fatura/medidor exigem resposta detalhada (volume + procedência + tipo medidor):
        # libera teto maior antes do clamp por contexto disponível.
        if _is_fatura_medidor_query(question):
            sla_cap = min(700, self.config.max_turn_tokens // 2)
        else:
            sla_cap = min(400, self.config.max_turn_tokens // 2)
        context_limit = min(self.config.n_ctx, self.config.max_context_tokens)
        fixed = self._fixed_prompt_tokens(
            question=question,
            history=history,
            history_summary=history_summary,
        )
        # Mantém folga mínima para ao menos 1 passagem curta no contexto.
        available = context_limit - fixed - 64
        return max(64, min(sla_cap, available))

    def _enforce_budget(
        self,
        passages: list[Passage],
        *,
        question: str = "",
        history: list[dict[str, str]] | None = None,
        history_summary: str | None = None,
    ) -> list[Passage]:
        context_limit = min(self.config.n_ctx, self.config.max_context_tokens)
        answer_budget = self._answer_budget(
            question=question,
            history=history,
            history_summary=history_summary,
        )
        fixed = self._fixed_prompt_tokens(
            question=question,
            history=history,
            history_summary=history_summary,
        )
        turn_cap = self.config.max_turn_tokens - 600
        # Reserva espaço para conclusão + overhead do render de contexto.
        budget = min(turn_cap, context_limit - fixed - answer_budget - 32)
        budget = max(80, budget)
        # Guarda adicional em caracteres para evitar prompt excessivo no chat template.
        char_budget = max(1_200, min(4_200, (context_limit - 1_200) * 2))
        acc = 0
        acc_chars = 0
        kept: list[Passage] = []
        for p in passages:
            passage_tokens = self._approx_tokens(p.text)
            passage_chars = len(p.text)
            if (
                acc + passage_tokens > budget
                or acc_chars + passage_chars > char_budget
            ):
                break
            kept.append(p)
            acc += passage_tokens
            acc_chars += passage_chars
        if kept:
            return kept
        if not passages:
            return []
        trim_budget = min(char_budget, max(160, budget * 3))
        return [self._trim_passage(passages[0], trim_budget)]

    @staticmethod
    def _approx_tokens(text: str) -> int:
        # Estimativa conservadora (PT-BR + markdown + IDs técnicos):
        # usar /3 reduz risco de undercount vs tokenizador real do modelo.
        return max(1, (len(text) + 2) // 3)

    def _fixed_prompt_tokens(
        self,
        *,
        question: str,
        history: list[dict[str, str]] | None,
        history_summary: str | None = None,
    ) -> int:
        history_tokens = sum(
            self._approx_tokens(str(turn.get("content", "")))
            for turn in (history or [])[-4:]
        )
        summary_tokens = self._approx_tokens(history_summary) if history_summary else 0
        # Prefixo estático + envelope ChatML + pergunta atual.
        return (
            self._approx_tokens(SYSTEM_STATIC)
            + self._approx_tokens(question)
            + history_tokens
            + summary_tokens
            + 80
        )

    def _trim_passage(self, passage: Passage, char_budget: int) -> Passage:
        trimmed = passage.text[: max(160, char_budget)].rstrip()
        if len(trimmed) < len(passage.text):
            trimmed = f"{trimmed}..."
        return replace(passage, text=trimmed)

    def _record(
        self,
        *,
        question: str,
        intent: str,
        passages: list[Passage],
        prompt_tokens: int,
        completion_tokens: int,
        first_token_ms: float,
        total_ms: float,
        region_detected: Literal["CE", "SP", "CE+SP"] | None,
        out_of_regional_scope: bool,
        golden_case_id: str | None,
        cache_hit: bool = False,
        extra: dict[str, Any] | None = None,
    ) -> None:
        try:
            regions = sorted({p.region for p in passages if p.region})
            telemetry = TurnTelemetry(
                ts=datetime.now(UTC).isoformat(),
                provider=getattr(self.provider, "name", "unknown"),
                model=getattr(self.provider, "model", "unknown"),
                question_hash=hash_question(question),
                question_preview=preview(question),
                intent_class=intent,
                region_detected=region_detected,
                region_of_passages=regions,
                out_of_regional_scope=out_of_regional_scope,
                golden_case_id=golden_case_id,
                n_passages=len(passages),
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                cache_hit=cache_hit,
                latency_first_token_ms=first_token_ms,
                latency_total_ms=total_ms,
                cost_usd_estimated=0.0,  # llama-cpp local
                extra={
                    "sources": [p.source_path for p in passages],
                    **(extra or {}),
                },
            )
            record(self.config.telemetry_path, telemetry)
        except Exception:
            # Telemetria nunca deve quebrar a experiência do usuário.
            pass


def format_citations(passages: list[Any]) -> str:
    """Renderiza bloco final com citações normalizadas no formato `[fonte: ...]`."""
    if not passages:
        return ""
    lines = ["", "---", "**Fontes:**"]
    seen: set[str] = set()
    for p in passages:
        key = f"{p.source_path}#{p.anchor}"
        if key in seen:
            continue
        seen.add(key)
        anchor = f"#{p.anchor}" if p.anchor else ""
        lines.append(f"- [fonte: {p.source_path}{anchor}]")
    return "\n".join(lines)


def _source_payload(passages: list[Passage]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for passage in passages:
        key = f"{passage.source_path}#{passage.anchor}"
        if key in seen:
            continue
        seen.add(key)
        out.append(
            {
                "doc_id": passage.chunk_id,
                "path": passage.source_path,
                "section": passage.section,
                "score": round(float(passage.score), 4),
                "anchor": passage.anchor,
            }
        )
    return out
