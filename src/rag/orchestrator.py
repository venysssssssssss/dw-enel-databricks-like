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

import re
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, Literal

from src.common.llm_gateway import build_provider
from src.rag.prompts import build_messages
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
    from collections.abc import Iterator

    from src.common.llm_gateway import LLMProvider
    from src.rag.config import RagConfig

_GREETING_RE = re.compile(
    r"^\s*(olá|ola|oi+|bom\s*dia|boa\s*tarde|boa\s*noite|hello|hi|hey|e\s*aí)\b",
    re.IGNORECASE,
)

_CE_RE = re.compile(r"(ceará|cearense|fortaleza|\bce\b)", re.IGNORECASE)
_SP_RE = re.compile(r"(são paulo|paulista|\bsp\b)", re.IGNORECASE)

ANALYTICAL_INTENTS = {"analise_dados"}

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

# Boosts determinísticos: cada regra casa a query e injeta cards canônicos na
# retrieval. Ordem importa — primeiros anchors têm prioridade visual no prompt.
# CE tem dois universos: (a) cards CE-total com 167k ordens reais e (b) cards
# CE+SP de erro_leitura rotulado. As regras abaixo casam primeiro os genéricos
# e depois a extensão CE-total é aplicada separadamente quando região=CE.
_CARD_BOOST_RULES: tuple[tuple[re.Pattern[str], tuple[str, ...]], ...] = (
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
    # Assuntos / tipos de reclamação
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
        ("ce-top-instalacoes", "sp-n1-top-instalacoes"),
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
        re.compile(r"\b(refatur\w*|maior taxa|mais refatur\w*|taxa de refatur\w*)\b", re.IGNORECASE),
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
            r"\b(instala\w*|\buc\b|ucs|cliente|clientes|consumidor|consumidores|medidor)\b",
            re.IGNORECASE,
        ),
        ("sp-n1-top-instalacoes",),
    ),
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
    return list(seen.keys())


def is_individual_client_query(question: str) -> bool:
    """Queries sobre cliente/UC individual: recusar cedo com orientação agregada."""
    return bool(_INDIVIDUAL_CLIENT_RE.search(question))


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
            "compare",
            "compar",
            "resumo",
            "dados",
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
        if not check.allowed:
            return RagResponse(
                text=check.reason or "Pergunta inválida.",
                passages=[],
                intent="blocked",
                prompt_tokens=0,
                completion_tokens=0,
                latency_ms=timer.total_ms(),
                blocked_reason=check.reason,
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
            )

        # MVP: perguntas sobre instalação/UC agora são roteadas para cards
        # `*-top-instalacoes` (via boosts). A recusa individual foi removida —
        # `INDIVIDUAL_CLIENT_MESSAGE` permanece disponível para rollback futuro.
        intent = classify_intent(check.sanitized)
        region = detect_regional_scope(check.sanitized)
        if region is None and intent in ANALYTICAL_INTENTS:
            region = "CE+SP"

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
            )

        passages = self._enforce_budget(passages)
        messages = build_messages(
            question=check.sanitized,
            passages=passages,
            history=history,
            history_summary=None,
        )
        resp = self.provider.complete(
            messages,
            max_tokens=self._answer_budget(),
            temperature=self.config.temperature,
            top_p=self.config.top_p,
        )
        timer.mark_first_token()
        text = sanitize_output(resp.text).strip()

        self._record(
            question=check.sanitized,
            intent=intent,
            passages=passages,
            prompt_tokens=resp.prompt_tokens,
            completion_tokens=resp.completion_tokens,
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
        )

    def stream_answer(
        self,
        question: str,
        *,
        history: list[dict[str, str]] | None = None,
        context_hint: str | None = None,
        dataset_version: str | None = None,
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
        if region is None and intent in ANALYTICAL_INTENTS:
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

        passages = self._enforce_budget(passages)
        messages = build_messages(
            question=check.sanitized, passages=passages, history=history
        )
        acc_text = []
        for chunk in self.provider.stream(
            messages,
            max_tokens=self._answer_budget(),
            temperature=self.config.temperature,
            top_p=self.config.top_p,
        ):
            timer.mark_first_token()
            acc_text.append(chunk)
            yield chunk
        joined = "".join(acc_text)
        sanitized = sanitize_output(joined)
        if sanitized != joined:
            # PII detectada pós-geração: emite correção clara (não silencia).
            yield "\n\n_[saída sanitizada — PII removida]_"

        self._record(
            question=check.sanitized,
            intent=intent,
            passages=passages,
            prompt_tokens=0,
            completion_tokens=len(joined) // 4,
            first_token_ms=timer.first_token_ms,
            total_ms=timer.total_ms(),
            region_detected=region,
            out_of_regional_scope=False,
            golden_case_id=None,
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
        # Primeiro passo: recuperação semântica + lexical padrão, mas pedindo
        # mais passages (2x top_n) para permitir merge com boosts sem perder
        # diversidade.
        kwargs: dict[str, Any] = {
            "top_n": top_n * 2,
            "doc_types": doc_types,
            "region": region,
        }
        if dataset_version:
            kwargs["dataset_version"] = dataset_version
        semantic = self.retriever.top_passages(query, **kwargs)

        # Segundo passo: boost determinístico — cards canônicos forçados no topo
        # quando a intenção da query é claramente identificável por keyword.
        forced_anchors = detect_card_boosts(query, region=region)
        if forced_anchors:
            forced = self.retriever.get_by_anchors(
                forced_anchors, dataset_version=dataset_version
            )
            # Filtra por região compatível quando especificada
            if region in {"CE", "SP"}:
                forced = [
                    p for p in forced
                    if p.region in {region, "CE+SP"}
                ]
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

    def _answer_budget(self) -> int:
        """Teto de tokens de resposta para SLA de ~35s em CPU (Qwen 2.5 3B Q4).

        Aproximação: ~12-14 tok/s em i7-1185G7 → 35s ≈ 400 tokens úteis.
        Respostas curtas e diretas também reforçam as regras de exatidão.
        """
        return min(400, self.config.max_turn_tokens // 2)

    def _enforce_budget(self, passages: list[Passage]) -> list[Passage]:
        budget = self.config.max_turn_tokens - 600  # reserva para system+pergunta+resposta
        acc = 0
        kept: list[Passage] = []
        for p in passages:
            if acc + (len(p.text) // 4) > budget:
                break
            kept.append(p)
            acc += len(p.text) // 4
        return kept or passages[:1]

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
                cache_hit=False,
                latency_first_token_ms=first_token_ms,
                latency_total_ms=total_ms,
                cost_usd_estimated=0.0,  # llama-cpp local
                extra={"sources": [p.source_path for p in passages]},
            )
            record(self.config.telemetry_path, telemetry)
        except Exception:
            # Telemetria nunca deve quebrar a experiência do usuário.
            pass


def format_citations(passages: list[Any]) -> str:
    """Renderiza bloco final com links markdown para as fontes."""
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
        lines.append(f"- [{p.source_path}{anchor}]({p.source_path}{anchor})")
    return "\n".join(lines)
