"""Templates de prompt (PT-BR) versionados.

Separação explícita estático/dinâmico facilita prompt caching em provedores
que suportam (Anthropic, OpenAI) e reduz tokens em LLMs locais (llama-cpp
tem KV cache automático: prefix constante acelera turnos subsequentes).
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.rag.retriever import Passage


PROMPT_VERSION = "1.0.0"

SYSTEM_STATIC = """Você é o Assistente ENEL, uma IA corporativa que responde sobre a \
plataforma analítica preditiva ENEL (data lakehouse open-source para a distribuidora \
de energia). Você é técnico, objetivo e escreve em português brasileiro.

REGRAS DE RESPOSTA:
1. Responda APENAS com base nos trechos de contexto fornecidos. Se o contexto for \
insuficiente, diga isso explicitamente em uma frase.
2. Sempre cite suas fontes no formato [fonte: caminho/do/arquivo.md#ancora]. \
Cite pelo menos uma fonte por parágrafo substantivo.
3. Não invente métricas, números ou nomes que não estejam no contexto.
4. Seja conciso: respostas típicas têm 3-6 parágrafos curtos.
5. Para perguntas técnicas, mostre comandos/caminhos/exemplos quando o contexto os \
contiver.
6. Nunca exponha CPF, e-mail, telefone ou dados pessoais. Se perguntarem sobre \
dados de cliente individual, recuse com uma frase e redirecione para métricas \
agregadas.

GLOSSÁRIO ENEL (use se mencionado pelo usuário):
- ACF/ASF: classificação de risco de ordem (vide docs/business-rules/).
- UC: unidade consumidora. Lote: agrupamento operacional. UT/CO: unidade técnica \
e centro operacional.
- Bronze/Silver/Gold: camadas do data lakehouse (ingestão crua / normalizado / \
dimensional).
- Macro-temas CE: refaturamento, geração distribuída, variação de consumo, \
média/estimativa, religação/multas, entrega de fatura, ouvidoria, outros.
"""


def build_messages(
    *,
    question: str,
    passages: Iterable["Passage"],
    history: list[dict[str, str]] | None = None,
    history_summary: str | None = None,
) -> list[dict[str, str]]:
    """Constrói mensagens no formato ChatML. Dinâmicas separadas do estático.

    Estrutura:
      [0] system: SYSTEM_STATIC (cacheável)
      [1] system: contexto recuperado + (opcional) resumo de histórico
      [2..n] últimos turnos íntegros
      [n+1] user: pergunta atual
    """
    passages = list(passages)
    context_block = _render_passages(passages) if passages else "(nenhum trecho relevante encontrado)"

    sections = [f"CONTEXTO RECUPERADO:\n\n{context_block}"]
    if history_summary:
        sections.append(f"RESUMO DA CONVERSA ANTERIOR:\n{history_summary}")

    messages: list[dict[str, str]] = [
        {"role": "system", "content": SYSTEM_STATIC},
        {"role": "system", "content": "\n\n".join(sections)},
    ]
    for turn in (history or [])[-4:]:
        role = turn.get("role", "user")
        if role not in {"user", "assistant"}:
            continue
        content = str(turn.get("content", "")).strip()
        if content:
            messages.append({"role": role, "content": content})

    messages.append({"role": "user", "content": question.strip()})
    return messages


def _render_passages(passages: list["Passage"]) -> str:
    lines: list[str] = []
    for i, p in enumerate(passages, start=1):
        header = f"[{i}] {p.source_path}"
        if p.anchor:
            header += f"#{p.anchor}"
        if p.section and p.section != "(sem título)":
            header += f" — {p.section}"
        lines.append(header)
        lines.append(p.text.strip())
        lines.append("")
    return "\n".join(lines).strip()


def build_summarize_history_prompt(history: list[dict[str, str]]) -> list[dict[str, str]]:
    """Prompt curto para compactar histórico em 1-2 frases."""
    turns = "\n".join(
        f"{t.get('role', 'user').upper()}: {str(t.get('content', ''))[:400]}"
        for t in history
    )
    return [
        {
            "role": "system",
            "content": "Resuma a conversa abaixo em 1-2 frases em português, "
            "preservando entidades (nomes de sprints, métricas, filtros). "
            "Responda APENAS com o resumo, sem prefácios.",
        },
        {"role": "user", "content": turns},
    ]


SUGGESTED_QUESTIONS: list[tuple[str, str]] = [
    ("O que é ACF/ASF?", "business"),
    ("Como o modelo de erro de leitura classifica os casos?", "ml"),
    ("Como interpretar o gráfico de radar por grupo?", "viz"),
    ("Como rodar o pipeline Bronze → Silver localmente?", "architecture"),
    ("Quais os KPIs da Sprint 13?", "sprint"),
    ("Quais macro-temas existem para reclamações CE?", "viz"),
    ("Como funciona a ingestão na camada Bronze?", "architecture"),
    ("Quais são as regras de PII na plataforma?", "business"),
]
