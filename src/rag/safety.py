"""Guardrails de entrada/saída para o chat RAG.

- PII: CPF, CNPJ, e-mail, telefone — mascarados em entrada e saída.
- Prompt injection: padrões conhecidos bloqueados na entrada.
- Out-of-scope: quando não há contexto suficiente, responde fallback educado.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_CPF_RE = re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b")
_CNPJ_RE = re.compile(r"\b\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}\b")
_EMAIL_RE = re.compile(r"\b[\w.-]+@[\w.-]+\.[A-Za-z]{2,}\b")
_PHONE_RE = re.compile(r"\b(?:\+?55\s?)?(?:\(?\d{2}\)?\s?)?9?\d{4}-?\d{4}\b")

_INJECTION_PATTERNS = (
    "ignore previous",
    "ignore all previous",
    "disregard the above",
    "ignore suas instruções",
    "ignore as instruções",
    "reveal your prompt",
    "mostre seu prompt",
    "system prompt:",
    "jailbreak",
    "DAN mode",
    "act as a different",
)

_OTHER_REGIONS = re.compile(
    r"\b(rio de janeiro|minas gerais|bahia|pernambuco|paraná|paraíba|"
    r"rio grande|goiás|mato grosso|santa catarina|amazonas|pará|maranhão|"
    r"alagoas|sergipe|piauí|tocantins|rondônia|acre|amapá|roraima|"
    r"espírito santo|distrito federal|\brj\b|\bmg\b|\bba\b|\bpe\b|\bpr\b|"
    r"\bpb\b|\brs\b|\bgo\b|\bmt\b|\bms\b|\bsc\b|\bam\b|\bpa\b|\bma\b|"
    r"\bal\b|\bse\b|\bpi\b|\bto\b|\bro\b|\bac\b|\bap\b|\brr\b|\bes\b|\bdf\b)",
    re.IGNORECASE,
)

_CE_SP_SCOPE = re.compile(r"(ceará|cearense|\bce\b|são paulo|paulista|\bsp\b)", re.IGNORECASE)

OUT_OF_SCOPE_MESSAGE = (
    "Não encontrei essa informação nos documentos da plataforma ENEL. "
    "Tente reformular a pergunta ou consulte diretamente os arquivos em `docs/`."
)


@dataclass(frozen=True, slots=True)
class InputCheck:
    allowed: bool
    sanitized: str
    reason: str = ""


def mask_pii(text: str) -> str:
    text = _CPF_RE.sub("[CPF]", text)
    text = _CNPJ_RE.sub("[CNPJ]", text)
    text = _EMAIL_RE.sub("[EMAIL]", text)
    text = _PHONE_RE.sub("[TELEFONE]", text)
    return text


def detect_injection(text: str) -> str | None:
    low = text.lower()
    for pat in _INJECTION_PATTERNS:
        if pat in low:
            return pat
    return None


def check_input(question: str) -> InputCheck:
    q = question.strip()
    if not q:
        return InputCheck(allowed=False, sanitized="", reason="empty")
    if len(q) > 2000:
        return InputCheck(
            allowed=False,
            sanitized="",
            reason="Pergunta muito longa (>2000 chars). Resuma, por favor.",
        )
    injection = detect_injection(q)
    if injection:
        return InputCheck(
            allowed=False,
            sanitized="",
            reason=f"Pergunta bloqueada por filtro de segurança (padrão: {injection!r}).",
        )
    return InputCheck(allowed=True, sanitized=mask_pii(q))


def sanitize_output(text: str) -> str:
    """Remove PII que o modelo possa ter gerado."""
    return mask_pii(text)


def is_out_of_scope(passages: list, threshold: float) -> bool:
    if not passages:
        return True
    best = max(p.score for p in passages)
    return best < threshold


def is_out_of_regional_scope(question: str) -> bool:
    q = question.lower()
    has_other = bool(_OTHER_REGIONS.search(q))
    has_ce_sp = bool(_CE_SP_SCOPE.search(q))
    return has_other and not has_ce_sp
