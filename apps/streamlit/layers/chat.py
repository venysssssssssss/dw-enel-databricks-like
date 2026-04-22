# ruff: noqa: E501
"""Aba '💬 Assistente ENEL' — chat RAG embarcado no dashboard."""

from __future__ import annotations

import html
import time
from datetime import datetime
from typing import Any

from src.rag.config import load_rag_config
from src.rag.orchestrator import (
    OUT_OF_REGIONAL_SCOPE_MESSAGE,
    RagOrchestrator,
    classify_intent,
    detect_regional_scope,
    greeting_response,
)
from src.rag.prompts import SUGGESTED_QUESTIONS
from src.rag.retriever import check_stub_corpus
from src.rag.safety import (
    OUT_OF_SCOPE_MESSAGE,
    check_input,
    is_out_of_regional_scope,
    is_out_of_scope,
)
from src.rag.telemetry import hash_question, log_feedback

_CHIP_CATEGORIES: dict[str, str] = {
    "business": "Regras",
    "ml": "Modelos",
    "viz": "Dashboard",
    "architecture": "Arquitetura",
    "sprint": "Sprints",
    "data": "Dados · CE+SP",
}

_DATA_QUESTIONS: list[tuple[str, str]] = [
    ("Quantas reclamações temos no total (CE + SP)?", "data"),
    ("Quais os top 5 assuntos de reclamação?", "data"),
    ("Qual a causa-raiz mais frequente?", "data"),
    ("Como foi a evolução mensal de reclamações?", "data"),
    ("Qual instalação mais gera reclamações em CE?", "data"),
    ("Como é calculado o flag ACF/ASF?", "business"),
]


_CHAT_CSS = """
<style>
/* ======================================================================
 * Chat — graphite premium  (vars bridged from theme.py aliases)
 * ====================================================================== */

/* ── Header ──────────────────────────────────────────────────────────── */
.chat-header {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 20px;
  padding: 8px 4px 20px;
  border-bottom: 1px solid var(--divider);
  margin-bottom: 24px;
  align-items: end;
}
.chat-title {
  font-family: var(--font-display);
  font-size: 28px;
  line-height: 1.15;
  font-weight: 600;
  letter-spacing: -0.02em;
  margin: 0 0 6px;
  color: var(--text);
}
.chat-subtitle {
  font-size: 13.5px;
  color: var(--text-muted);
  max-width: 560px;
  margin: 0;
  line-height: 1.55;
}
.chat-subtitle code {
  font-family: var(--font-mono);
  font-size: 12px;
  padding: 1px 5px;
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-radius: 4px;
  color: var(--text);
}

/* ── Status strip ────────────────────────────────────────────────────── */
.status-strip {
  display: grid;
  grid-auto-flow: column;
  gap: 20px;
  padding: 0;
}
.status-cell {
  display: grid;
  gap: 3px;
  min-width: 100px;
}
.status-cell .k {
  font-family: var(--font-mono);
  font-size: 10px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--text-faint);
  font-weight: 500;
}
.status-cell .v {
  font-family: var(--font-mono);
  font-size: 12px;
  color: var(--text);
  font-weight: 500;
  display: flex;
  align-items: center;
  gap: 6px;
}
.status-cell .v .dot {
  width: 6px; height: 6px; border-radius: 50%;
  flex-shrink: 0;
}
.status-cell .v.ok .dot {
  background: var(--ok);
  box-shadow: 0 0 0 3px oklch(70% 0.14 150 / 0.2);
}
.status-cell .v.warn .dot {
  background: var(--warn);
  box-shadow: 0 0 0 3px oklch(74% 0.14 70 / 0.2);
}

/* ── Intro callout ───────────────────────────────────────────────────── */
.chat-intro {
  padding: 16px 18px;
  border: 1px solid var(--border);
  border-left: 3px solid var(--accent);
  border-radius: var(--r-md);
  background: var(--surface);
  margin-bottom: 24px;
  display: grid;
  gap: 6px;
}
.chat-intro h4 {
  margin: 0;
  font-size: 12px;
  font-family: var(--font-mono);
  font-weight: 500;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--text-faint);
}
.chat-intro p {
  margin: 0;
  font-size: 13.5px;
  color: var(--text-muted);
  line-height: 1.55;
}
.chat-intro p b { color: var(--text); font-weight: 600; }
.chat-intro code {
  font-family: var(--font-mono);
  font-size: 12px;
  padding: 1px 5px;
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-radius: 4px;
  color: var(--text);
}

/* ── Suggest grid ────────────────────────────────────────────────────── */
.sug-grid-label {
  font-family: var(--font-mono);
  font-size: 11px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--text-faint);
  margin-bottom: 10px;
  font-weight: 500;
}

/* Style st.button inside .sug-grid to look like sug-cards */
.sug-grid [data-testid="column"] .stButton > button {
  background: var(--surface) !important;
  border: 1px solid var(--border) !important;
  border-radius: var(--r-md) !important;
  text-align: left !important;
  min-height: 72px !important;
  height: auto !important;
  white-space: normal !important;
  padding: 12px 14px !important;
  font-size: 13px !important;
  font-weight: 500 !important;
  color: var(--text) !important;
  line-height: 1.4 !important;
  transition: all 160ms var(--ease) !important;
  width: 100% !important;
}
.sug-grid [data-testid="column"] .stButton > button:hover {
  border-color: var(--border-strong) !important;
  transform: translateY(-1px) !important;
  box-shadow: var(--shadow-md) !important;
  color: var(--text) !important;
}

/* ── Messages ────────────────────────────────────────────────────────── */
.msg {
  display: grid;
  grid-template-columns: 32px 1fr;
  gap: 14px;
  margin-bottom: 24px;
  animation: msgIn 220ms var(--ease) both;
}
@keyframes msgIn {
  from { opacity: 0; transform: translateY(4px); }
  to   { opacity: 1; transform: translateY(0); }
}
.msg-avatar {
  width: 32px; height: 32px;
  border-radius: 8px;
  display: grid; place-items: center;
  font-family: var(--font-mono);
  font-size: 11px;
  font-weight: 600;
  border: 1px solid var(--border);
  background: var(--surface);
  color: var(--text-muted);
  user-select: none;
  flex-shrink: 0;
}
.msg.user .msg-avatar {
  background: var(--surface-2);
  color: var(--text);
}
.msg.assistant .msg-avatar {
  background: linear-gradient(135deg, var(--accent) 0%, oklch(44% 0.18 15) 100%);
  color: #fff;
  border-color: transparent;
  box-shadow: inset 0 -6px 10px rgba(0,0,0,0.25);
  position: relative;
}
.msg.assistant .msg-avatar::before {
  content: "";
  position: absolute; top: 4px; right: 4px;
  width: 3px; height: 3px; border-radius: 50%;
  background: rgba(255,255,255,0.8);
}
.msg-body { display: grid; gap: 10px; min-width: 0; }
.msg-head {
  display: flex; align-items: center; gap: 10px;
  font-size: 12px;
  color: var(--text-faint);
}
.msg-head .name {
  font-family: var(--font-display);
  font-weight: 600;
  color: var(--text);
  font-size: 13px;
  letter-spacing: -0.005em;
}
.msg-head .time { font-family: var(--font-mono); font-size: 11px; }
.msg-head .badge {
  font-family: var(--font-mono);
  font-size: 10px;
  padding: 1px 5px;
  border: 1px solid var(--border);
  border-radius: 3px;
  color: var(--text-dim);
}
.msg-text {
  font-size: 14px;
  line-height: 1.65;
  color: var(--text);
  max-width: 72ch;
}
.msg-text p { margin: 0 0 8px; }
.msg-text p:last-child { margin-bottom: 0; }
.msg-text b { font-weight: 600; }
.msg-text code {
  font-family: var(--font-mono);
  font-size: 12.5px;
  padding: 1px 5px;
  background: var(--surface-2);
  border-radius: 4px;
  border: 1px solid var(--border);
}
.msg.assistant .msg-text {
  padding-left: 14px;
  border-left: 2px solid var(--divider);
}

/* ── Agent step spoilers (pipeline peek — LIVE animations) ───────────── */
.agent-steps {
  display: grid;
  gap: 6px;
  padding: 14px 16px;
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-left: 3px solid var(--accent);
  border-radius: var(--r-md);
  margin-bottom: 12px;
  max-width: 640px;
  position: relative;
  overflow: hidden;
}
.agent-steps::before {
  content: "";
  position: absolute;
  inset: 0;
  background: linear-gradient(
    110deg,
    transparent 30%,
    var(--accent-soft) 50%,
    transparent 70%
  );
  background-size: 220% 100%;
  animation: agCardSweep 4.2s linear infinite;
  pointer-events: none;
  opacity: 0.55;
}
@keyframes agCardSweep {
  from { background-position: 180% 0; }
  to   { background-position: -80% 0; }
}
.agent-steps > * { position: relative; z-index: 1; }

.agent-steps .ag-title {
  font-family: var(--font-mono);
  font-size: 10.5px;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--text-faint);
  font-weight: 600;
  margin-bottom: 4px;
  display: flex; align-items: center; gap: 8px;
}
.agent-steps .ag-title .live {
  width: 7px; height: 7px; border-radius: 50%;
  background: var(--accent);
  box-shadow: 0 0 0 0 var(--accent-ring);
  animation: liveDot 1.4s ease-in-out infinite;
  flex-shrink: 0;
}
@keyframes liveDot {
  0%, 100% { opacity: 0.55; transform: scale(1); box-shadow: 0 0 0 0 var(--accent-ring); }
  50%      { opacity: 1;    transform: scale(1.25); box-shadow: 0 0 0 6px transparent; }
}

.ag-row {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 12.5px;
  color: var(--text-muted);
  font-family: var(--font-body);
  padding: 3px 6px;
  margin-left: -6px;
  border-radius: 6px;
  animation: stepIn 260ms var(--ease) both;
  position: relative;
}
@keyframes stepIn {
  from { opacity: 0; transform: translateX(-4px); }
  to   { opacity: 1; transform: translateX(0); }
}

/* Active row — continuous aliveness (bg sweep + glow) */
.ag-row.active {
  background: linear-gradient(
    90deg,
    transparent 0%,
    var(--accent-soft) 35%,
    var(--accent-soft) 65%,
    transparent 100%
  );
  background-size: 260% 100%;
  animation: stepIn 260ms var(--ease) both,
             bgSweep 2.4s cubic-bezier(.45,0,.55,1) infinite;
}
@keyframes bgSweep {
  from { background-position: 130% 0; }
  to   { background-position: -130% 0; }
}

.ag-row .mark {
  width: 16px; height: 16px; border-radius: 50%;
  display: grid; place-items: center;
  font-size: 10px; font-weight: 600;
  font-family: var(--font-mono);
  flex-shrink: 0;
}
.ag-row.done .mark {
  background: oklch(70% 0.14 150 / 0.18);
  color: var(--ok);
  border: 1px solid oklch(70% 0.14 150 / 0.40);
  animation: markPop 340ms var(--ease) both;
}
.ag-row.done .mark::before { content: "✓"; }
@keyframes markPop {
  0%   { transform: scale(0.6); opacity: 0; }
  60%  { transform: scale(1.18); opacity: 1; }
  100% { transform: scale(1); }
}
.ag-row.active .mark {
  border: 2px solid var(--accent-ring);
  border-top-color: var(--accent);
  animation: agSpin 0.75s linear infinite;
}
@keyframes agSpin { to { transform: rotate(360deg); } }
.ag-row.pending .mark {
  border: 1px dashed var(--border-strong);
  opacity: 0.7;
}
.ag-row.pending { opacity: 0.42; }

.ag-row .lbl {
  color: var(--text);
  font-weight: 500;
  flex-shrink: 0;
  white-space: nowrap;
}
.ag-row.pending .lbl { color: var(--text-faint); font-weight: 400; }

/* Inline trace — scrolling substream next to label (GPT/DeepSeek thinking feel) */
.ag-row .ag-trace {
  flex: 1;
  min-width: 0;
  height: 16px;
  position: relative;
  overflow: hidden;
}
.ag-row:not(.active) .ag-trace { display: none; }
.ag-trace .tr {
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 16px;
  line-height: 16px;
  font-family: var(--font-mono);
  font-size: 10.5px;
  color: var(--text-dim);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  opacity: 0;
  transform: translateY(6px);
  animation: traceRotate 6s infinite;
}
.ag-trace .tr::before {
  content: "›";
  margin-right: 5px;
  color: var(--accent);
  opacity: 0.75;
}
.ag-trace .tr:nth-child(1) { animation-delay: 0.0s; }
.ag-trace .tr:nth-child(2) { animation-delay: 1.2s; }
.ag-trace .tr:nth-child(3) { animation-delay: 2.4s; }
.ag-trace .tr:nth-child(4) { animation-delay: 3.6s; }
.ag-trace .tr:nth-child(5) { animation-delay: 4.8s; }
/* 5 items × 1.2s window = 6s total cycle */
@keyframes traceRotate {
  0%    { opacity: 0; transform: translateY(6px); }
  3%    { opacity: 1; transform: translateY(0); }
  17%   { opacity: 1; transform: translateY(0); }
  20%   { opacity: 0; transform: translateY(-6px); }
  100%  { opacity: 0; transform: translateY(-6px); }
}

.ag-row .detail {
  font-family: var(--font-mono);
  font-size: 10.5px;
  color: var(--text-faint);
  flex-shrink: 0;
  white-space: nowrap;
  padding: 1px 6px;
  border-radius: 4px;
  background: var(--surface);
  border: 1px solid var(--border);
}
.ag-row.done .detail {
  color: var(--accent);
  border-color: var(--accent-ring);
}
.ag-row.active .detail {
  color: var(--text);
  background: var(--surface);
  border-color: var(--accent-ring);
}

@media (prefers-reduced-motion: reduce) {
  .agent-steps::before,
  .ag-row.active,
  .ag-row.active .mark,
  .agent-steps .ag-title .live,
  .ag-trace .tr {
    animation: none !important;
  }
  .ag-trace .tr:nth-child(1) { opacity: 1; transform: none; }
  .ag-row.active { background: var(--accent-soft); }
}

/* ── Typing shimmer ──────────────────────────────────────────────────── */
.typing { display: grid; gap: 8px; max-width: 480px; }
.typing-label {
  font-family: var(--font-mono);
  font-size: 11.5px;
  color: var(--text-muted);
  display: flex; align-items: center; gap: 8px;
}
.typing-label .pulse {
  width: 7px; height: 7px; border-radius: 50%;
  background: var(--accent);
  animation: pulse 1.4s ease-in-out infinite;
  flex-shrink: 0;
}
@keyframes pulse {
  0%, 100% { opacity: 0.3; transform: scale(1); }
  50%       { opacity: 1;   transform: scale(1.2); }
}
.shimmer {
  height: 6px;
  border-radius: 3px;
  background: var(--surface-2);
  overflow: hidden;
  position: relative;
}
.shimmer::after {
  content: "";
  position: absolute; inset: 0;
  background: linear-gradient(
    90deg,
    transparent 0%,
    var(--accent-soft) 30%,
    var(--accent) 50%,
    var(--accent-soft) 70%,
    transparent 100%
  );
  animation: shimmerMove 1.4s linear infinite;
  width: 50%;
}
@keyframes shimmerMove {
  0%   { transform: translateX(-100%); }
  100% { transform: translateX(400%); }
}
.shimmer.s2 { width: 75%; opacity: 0.55; }
.shimmer.s3 { width: 50%; opacity: 0.35; }

/* ── Completion pill row (replaces done-state iframe re-mount) ──────── */
.completion-pill-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  margin: 0 0 14px;
  max-width: 640px;
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-left: 3px solid var(--ok);
  border-radius: var(--r-md);
  animation: msgIn 260ms var(--ease) both;
}
.completion-done {
  font-family: var(--font-mono);
  font-size: 11px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--ok);
  font-weight: 600;
  margin-right: 4px;
}

/* ── Sources ─────────────────────────────────────────────────────────── */
.sources {
  margin-top: 12px;
  padding: 10px 12px;
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-radius: var(--r-md);
}
.sources-head {
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--text-faint);
  letter-spacing: 0.06em;
  text-transform: uppercase;
  margin-bottom: 8px;
  display: flex; align-items: center; gap: 8px;
}
.sources-head .count {
  color: var(--text);
  padding: 0 5px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 3px;
}
.sources-list { display: grid; gap: 3px; }
.source {
  display: grid;
  grid-template-columns: 20px 1fr auto;
  gap: 8px;
  align-items: center;
  padding: 5px 6px;
  border-radius: 5px;
  font-size: 12px;
  color: var(--text-muted);
}
.source .n {
  font-family: var(--font-mono);
  font-size: 10.5px;
  color: var(--text-faint);
  text-align: right;
}
.source .path { font-family: var(--font-mono); font-size: 11.5px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.source .score {
  font-family: var(--font-mono);
  font-size: 10.5px;
  color: var(--accent);
  padding: 1px 4px;
  background: var(--accent-soft);
  border-radius: 3px;
  white-space: nowrap;
}

/* ── Metadata pills ──────────────────────────────────────────────────── */
.meta-row {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 10px;
}
.pill {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 3px 7px;
  border-radius: 4px;
  font-family: var(--font-mono);
  font-size: 10.5px;
  color: var(--text-muted);
  background: var(--surface);
  border: 1px solid var(--border);
  line-height: 1.5;
}
.pill .k { color: var(--text-faint); }
.pill .v { color: var(--text); font-weight: 500; }
.pill.ok   .v { color: var(--ok); }
.pill.warn .v { color: var(--warn); }
.pill.crit .v { color: var(--crit); }

/* ── Feedback row ────────────────────────────────────────────────────── */
.fb-row-wrap {
  margin-top: -8px;
  margin-bottom: 8px;
  padding-left: 46px;
}
.fb-row-wrap .stButton > button {
  width: 34px !important; height: 30px !important;
  min-height: unset !important;
  padding: 0 !important;
  border: 1px solid var(--border-strong) !important;
  border-radius: 5px !important;
  background: var(--surface-2) !important;
  color: var(--text) !important;
  font-size: 13px !important;
  font-weight: 700 !important;
  display: grid !important;
  place-items: center !important;
  transition: all 140ms var(--ease) !important;
}
.fb-row-wrap .stButton > button:hover {
  color: var(--accent) !important;
  border-color: var(--accent-ring) !important;
  background: var(--accent-soft) !important;
}
.fb-row-wrap .stButton > button:focus-visible {
  outline: 2px solid var(--accent) !important;
  outline-offset: 2px !important;
}

/* ── Caret ───────────────────────────────────────────────────────────── */
.caret {
  display: inline-block;
  width: 2px; height: 1em;
  vertical-align: -2px;
  background: var(--accent);
  animation: caretBlink 1s steps(1) infinite;
  margin-left: 2px;
}
@keyframes caretBlink { 50% { opacity: 0; } }

/* ── Chat input — sticky premium bar ─────────────────────────────────── */
[data-testid="stChatInput"] {
  background: linear-gradient(
    180deg,
    transparent 0%,
    var(--bg) 40%,
    var(--bg) 100%
  ) !important;
  padding-top: 18px !important;
  padding-bottom: 6px !important;
}
[data-testid="stChatInput"] > div {
  background: var(--surface) !important;
  border: 1px solid var(--border-strong) !important;
  border-radius: var(--r-lg) !important;
  box-shadow: var(--shadow-md) !important;
  transition: border-color 180ms var(--ease), box-shadow 180ms var(--ease),
              transform 180ms var(--ease) !important;
}
[data-testid="stChatInput"] > div:focus-within {
  border-color: var(--accent) !important;
  box-shadow: 0 0 0 4px var(--accent-ring), var(--shadow-lg) !important;
  transform: translateY(-1px) !important;
}
[data-testid="stChatInput"] textarea {
  font-family: var(--font-body) !important;
  font-size: 14px !important;
  background: transparent !important;
  color: var(--text) !important;
  border: none !important;
  box-shadow: none !important;
  padding: 14px 16px !important;
  line-height: 1.55 !important;
  caret-color: var(--accent) !important;
}
[data-testid="stChatInput"] textarea::placeholder {
  color: var(--text-faint) !important;
  font-style: italic;
}
[data-testid="stChatInput"] button {
  background: var(--accent) !important;
  border-radius: var(--r-md) !important;
  color: #fff !important;
  transition: background 160ms var(--ease), transform 160ms var(--ease) !important;
}
[data-testid="stChatInput"] button:hover {
  background: var(--accent-hover) !important;
  transform: scale(1.04) !important;
}
[data-testid="stChatInput"] button[disabled] {
  background: var(--surface-3) !important;
  color: var(--text-faint) !important;
}

/* Accessibility */
:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; border-radius: 3px; }
</style>
"""


def render(st: Any, *, theme: str = "light", context_hint: str | None = None) -> None:
    st.markdown(_CHAT_CSS, unsafe_allow_html=True)

    orch = _build_orchestrator(st)
    config = st.session_state["rag_config"]
    corpus_ready = check_stub_corpus(config.chromadb_path)
    provider_name = getattr(orch.provider, "name", "stub")
    model_name = getattr(orch.provider, "model", "?")

    _render_chat_header(st, provider_name, model_name, corpus_ready, context_hint)
    _render_suggested_panel(st)
    _render_chat_area(st, orch, config, context_hint, theme=theme)


def _render_chat_header(
    st: Any,
    provider: str,
    model: str,
    corpus_ready: bool,
    context_hint: str | None,
) -> None:
    corpus_cls = "ok" if corpus_ready else "warn"
    corpus_lbl = "pronto" if corpus_ready else "vazio"
    provider_cls = "ok" if provider == "llama_cpp" else "warn"
    context_html = (
        f"<br>Contexto recebido: <code>{html.escape(context_hint)}</code>"
        if context_hint
        else ""
    )
    st.markdown(
        f"""
        <div class="chat-header">
          <div>
            <h1 class="chat-title">Assistente analítico</h1>
            <p class="chat-subtitle">RAG open-source, execução local em CPU.
              Indexa <code>docs/**</code> + data cards reais CE/SP
              (reclamações totais + N1).{context_html}</p>
          </div>
          <div class="status-strip">
            <div class="status-cell">
              <span class="k">Modelo</span>
              <span class="v">{model}</span>
            </div>
            <div class="status-cell">
              <span class="k">Provider</span>
              <span class="v {provider_cls}">
                <span class="dot"></span>{provider} · local
              </span>
            </div>
            <div class="status-cell">
              <span class="k">Índice</span>
              <span class="v {corpus_cls}">
                <span class="dot"></span>{corpus_lbl}
              </span>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if not corpus_ready:
        st.caption("Rode `python scripts/rebuild_rag_corpus_regional.py` para indexar.")
    if provider == "stub":
        st.caption(
            "Sem LLM ativo. Instale `llama-cpp-python` e baixe o GGUF via "
            "`scripts/build_rag_corpus.py --download-model`."
        )


def _build_orchestrator(st: Any) -> RagOrchestrator:
    if "rag_orchestrator" not in st.session_state:
        config = load_rag_config()
        st.session_state["rag_config"] = config
        with st.spinner("Carregando modelo local (Qwen2.5-3B)…"):
            st.session_state["rag_orchestrator"] = RagOrchestrator(config)
    return st.session_state["rag_orchestrator"]


def _render_suggested_panel(st: Any) -> None:
    st.markdown(
        "<div class='sug-grid-label'>Perguntas prontas</div>",
        unsafe_allow_html=True,
    )
    all_questions: list[tuple[str, str]] = list(SUGGESTED_QUESTIONS) + _DATA_QUESTIONS
    priority = all_questions[:9]
    rows = [priority[i : i + 3] for i in range(0, len(priority), 3)]

    st.markdown("<div class='sug-grid'>", unsafe_allow_html=True)
    for row_idx, row in enumerate(rows):
        cols = st.columns(len(row))
        for col_idx, (question, tag) in enumerate(row):
            cat = _CHIP_CATEGORIES.get(tag, tag)
            with cols[col_idx]:
                label = f"{cat}  \n{question}"
                if st.button(
                    label,
                    key=f"sug_{tag}_{row_idx}_{col_idx}",
                    use_container_width=True,
                ):
                    st.session_state["pending_question"] = question
                    st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)


def _render_chat_area(
    st: Any,
    orch: RagOrchestrator,
    config: Any,
    context_hint: str | None,
    *,
    theme: str = "light",
) -> None:
    if "chat_history" not in st.session_state:
        st.session_state["chat_history"] = []
        st.session_state["chat_first_open"] = True

    if st.session_state.get("chat_first_open") and not st.session_state["chat_history"]:
        st.markdown(_render_chat_intro(), unsafe_allow_html=True)

    for i, turn in enumerate(st.session_state["chat_history"]):
        _render_turn(st, turn, idx=i)

    pending = st.session_state.pop("pending_question", None)
    user_input = st.chat_input("Pergunte sobre dados, regras, arquitetura ou sprints") or pending
    if user_input:
        _handle_user_turn(st, orch, config, user_input, context_hint, theme=theme)

    bottom_cols = st.columns([1, 1, 4])
    with bottom_cols[0]:
        if st.session_state.get("chat_history") and st.button(
            "Limpar", use_container_width=True
        ):
            st.session_state["chat_history"] = []
            st.session_state["chat_first_open"] = True
            st.rerun()


def _render_turn(st: Any, turn: dict[str, Any], *, idx: int) -> None:
    role = turn["role"]
    name = "Você" if role == "user" else "Assistente"
    meta = turn.get("meta") or {}
    intent = meta.get("intent", "")
    badges: list[str] = []
    if role == "assistant" and intent:
        badges.append(f"intent · {intent}")
    time_str = turn.get("time_str", "")

    body_html = str(turn.get("content", ""))
    sources_html = _render_sources_html(turn.get("passages", []))

    html = (
        _bubble_open(role, name, badges, time_str)
        + body_html
        + sources_html
        + _bubble_close()
    )
    st.markdown(html, unsafe_allow_html=True)

    if role == "assistant":
        if meta:
            st.markdown(_format_metadata(meta), unsafe_allow_html=True)
        _render_feedback_row(st, turn, idx=idx)


def _handle_user_turn(
    st: Any,
    orch: RagOrchestrator,
    config: Any,
    user_input: str,
    context_hint: str | None,
    *,
    theme: str = "light",
) -> None:
    st.session_state["chat_first_open"] = False
    time_str = datetime.now().strftime("%H:%M")
    user_turn: dict[str, Any] = {
        "role": "user",
        "content": user_input,
        "time_str": time_str,
    }
    st.session_state["chat_history"].append(user_turn)
    st.markdown(
        _bubble_open("user", "Você", [], time_str) + user_input + _bubble_close(),
        unsafe_allow_html=True,
    )

    history = _history_for_llm(st.session_state["chat_history"])
    meta, full_text, passages = _stream_answer(
        st, orch, config, user_input, history, context_hint, theme=theme
    )

    if meta:
        st.markdown(_format_metadata(meta), unsafe_allow_html=True)

    turn: dict[str, Any] = {
        "role": "assistant",
        "content": full_text,
        "passages": passages,
        "meta": meta,
        "time_str": time_str,
        "q_hash": hash_question(user_input),
    }
    st.session_state["chat_history"].append(turn)
    _render_feedback_row(st, turn, idx=len(st.session_state["chat_history"]) - 1)
    st.rerun()


def _stream_answer(
    st: Any,
    orch: RagOrchestrator,
    config: Any,
    question: str,
    history: list[dict[str, str]],
    context_hint: str | None,
    *,
    theme: str = "light",
) -> tuple[dict[str, Any] | None, str, list]:
    """Run the RAG pipeline with streaming. Returns (meta, body_text, passages)."""
    start = time.perf_counter()

    # Two INDEPENDENT slots: thinking (iframe) and bubble (markdown). The iframe
    # is mounted AT MOST ONCE per turn — never re-mounted — so CSS animations
    # never restart. It stays in 'live' mode until the turn ends, then the slot
    # is cleared and a compact metrics pill is rendered inline.
    import streamlit.components.v1 as components  # local import

    thinking_slot = st.empty()
    bubble_slot = st.empty()
    metrics_slot = st.empty()
    badges: list[str] = []
    iframe_mounted = False

    def _mount_thinking() -> None:
        nonlocal iframe_mounted
        if iframe_mounted:
            return
        with thinking_slot.container():
            components.html(
                _thinking_component_html(theme=theme), height=220, scrolling=False
            )
        iframe_mounted = True

    def _clear_thinking() -> None:
        thinking_slot.empty()

    def _paint_bubble(body_html: str = "") -> None:
        bubble_slot.markdown(
            _bubble_open("assistant", "Assistente", badges)
            + body_html
            + _bubble_close(),
            unsafe_allow_html=True,
        )

    # ── Fast-path guards (no iframe for these) ─────────────────────────────
    check = check_input(question)
    if not check.allowed:
        msg = check.reason or "Pergunta inválida."
        _clear_thinking()
        st.warning(msg)
        return None, msg, []

    if is_out_of_regional_scope(check.sanitized):
        _clear_thinking()
        st.info(OUT_OF_REGIONAL_SCOPE_MESSAGE)
        elapsed = (time.perf_counter() - start) * 1000
        return {
            "intent": "out_of_regional_scope",
            "prompt_tokens": 0,
            "completion_tokens": len(OUT_OF_REGIONAL_SCOPE_MESSAGE) // 4,
            "latency_ms": elapsed,
            "sources": 0,
        }, OUT_OF_REGIONAL_SCOPE_MESSAGE, []

    intent = classify_intent(check.sanitized)
    badges = [f"intent · {intent}"]

    if intent in {"saudacao", "cortesia"}:
        text = greeting_response(context_hint)
        elapsed = (time.perf_counter() - start) * 1000
        _clear_thinking()
        _paint_bubble(text)
        return {
            "intent": intent,
            "prompt_tokens": 0,
            "completion_tokens": len(text) // 4,
            "latency_ms": elapsed,
            "sources": 0,
        }, text, []

    region = detect_regional_scope(check.sanitized)
    if region is None and intent == "analise_dados":
        region = "CE+SP"
    badges = [f"intent · {intent}", f"região · {region or 'geral'}"]

    # ── Real pipeline: mount iframe ONCE, then never touch it again ────────
    _mount_thinking()
    _paint_bubble("")

    _paint_bubble(_typing_block())

    try:
        response = orch.answer(
            check.sanitized,
            history=history,
            context_hint=context_hint,
            dataset_version=None,
        )
    except (FileNotFoundError, RuntimeError) as exc:
        _clear_thinking()
        msg = (
            "Índice RAG não disponível. Rode "
            "`python scripts/rebuild_rag_corpus_regional.py`.\n\n"
            f"_{exc}_"
        )
        st.warning(msg)
        return None, msg, []
    except Exception as exc:  # pragma: no cover - UI safety net
        _clear_thinking()
        msg = f"Falha ao gerar resposta RAG: {exc}"
        st.error(msg)
        return None, msg, []

    passages = response.passages
    if response.blocked_reason == "out_of_scope" or is_out_of_scope(
        passages, config.similarity_threshold
    ):
        _clear_thinking()
        st.info(OUT_OF_SCOPE_MESSAGE)
        return None, OUT_OF_SCOPE_MESSAGE, passages

    body = response.text.strip()
    sources_html = _render_sources_html(passages)
    elapsed = response.latency_ms or (time.perf_counter() - start) * 1000
    time_str = _format_duration_ms(elapsed)
    badges = [f"intent · {response.intent}", f"região · {response.region_detected or region or 'geral'}"]
    if response.cache_hit:
        badges.append("cache · hit")

    # Clear the thinking iframe and render a compact completion pill in its
    # place. Single deterministic transition — no iframe re-mount, no
    # animation restart.
    _clear_thinking()
    metrics_slot.markdown(
        _completion_pill_html(
            total_time_ms=elapsed,
            first_token_ms=None,
            tokens=response.completion_tokens,
            sources=len(passages),
        ),
        unsafe_allow_html=True,
    )

    # Final bubble with sources
    bubble_slot.markdown(
        _bubble_open("assistant", "Assistente", badges, time_str)
        + body
        + sources_html
        + _bubble_close(),
        unsafe_allow_html=True,
    )

    return {
        "intent": response.intent,
        "prompt_tokens": response.prompt_tokens,
        "completion_tokens": response.completion_tokens,
        "latency_ms": elapsed,
        "first_token_ms": None,
        "sources": len(passages),
        "cache_hit": response.cache_hit,
        "cache_seed_id": response.cache_seed_id,
    }, body, passages


# ── HTML helpers ─────────────────────────────────────────────────────────────


def _bubble_open(role: str, name: str, badges: list[str], time_str: str = "") -> str:
    avatar = "VC" if role == "user" else "A"
    badges_html = "".join(f"<span class='badge'>{b}</span>" for b in badges)
    time_html = f"<span class='time'>{time_str}</span>" if time_str else ""
    return (
        f"<div class='msg {role}'>"
        f"<div class='msg-avatar'>{avatar}</div>"
        f"<div class='msg-body'>"
        f"<div class='msg-head'>"
        f"<span class='name'>{name}</span>"
        f"{badges_html}{time_html}"
        f"</div>"
        f"<div class='msg-text'>"
    )


def _bubble_close() -> str:
    return "</div></div></div>"


_THINKING_STEPS_JS = [
    {
        "key": "sanitize",
        "label": "Validando entrada",
        "substream": [
            "scan prompt · normalizando NFKC",
            "mask PII · telefone/CPF/email",
            "policy check · safety layer",
            "comprimento · vs limite 2k tok",
            "hash determinístico da query",
        ],
    },
    {
        "key": "intent",
        "label": "Classificando intenção",
        "substream": [
            "tokenize · regex + fallback",
            "score vs 8 classes canônicas",
            "top-1 vs top-2 gap",
            "confidence gate · 0.55",
            "decisão final · roteia pipeline",
        ],
    },
    {
        "key": "region",
        "label": "Detectando escopo regional",
        "substream": [
            "regex CE|SP|Ceará|São Paulo",
            "fuzzy match cidades/uts",
            "fallback CE+SP se analítico",
            "out-of-scope check",
            "escopo validado",
        ],
    },
    {
        "key": "retrieve",
        "label": "Recuperando passagens RAG",
        "substream": [
            "embedding · MiniLM-L12 multilíngue",
            "Chroma ANN · k=32 vizinhos",
            "BM25 re-rank sobre keywords",
            "filter doc_types · cards+docs",
            "dedup por source_hash",
        ],
    },
    {
        "key": "budget",
        "label": "Ajustando orçamento de contexto",
        "substream": [
            "token-count por passagem",
            "corta excedentes · janela ctx",
            "reserva 512 tok p/ saída",
            "ordena por score descendente",
            "ctx-window Qwen 2.5 · 4k",
        ],
    },
    {
        "key": "llm",
        "label": "Gerando resposta",
        "substream": [
            "monta system prompt v2",
            "injeta passages como evidence",
            "few-shot CE/SP examples",
            "Qwen2.5-3B · CPU local",
            "stream tokens · citação ao fim",
        ],
    },
]


_THINKING_VARS_LIGHT = """\
  --surface: oklch(100% 0 0);
  --surface-2: oklch(97% 0.003 260);
  --border: oklch(90% 0.004 260);
  --border-strong: oklch(82% 0.005 260);
  --text: oklch(18% 0.008 260);
  --text-muted: oklch(40% 0.006 260);
  --text-dim: oklch(54% 0.005 260);
  --text-faint: oklch(68% 0.004 260);
"""

_THINKING_VARS_DARK = """\
  --surface: oklch(20% 0.006 260);
  --surface-2: oklch(23% 0.006 260);
  --border: oklch(28% 0.006 260);
  --border-strong: oklch(36% 0.006 260);
  --text: oklch(96% 0.002 260);
  --text-muted: oklch(70% 0.004 260);
  --text-dim: oklch(54% 0.004 260);
  --text-faint: oklch(42% 0.004 260);
"""


def _thinking_component_html(
    *,
    passages: list | None = None,
    done: bool = False,
    total_time_ms: float | None = None,
    first_token_ms: float | None = None,
    tokens: int | None = None,
    theme: str = "light",
) -> str:
    """Self-contained iframe HTML. Pure CSS animations + tiny JS state machine.
    Lives in an isolated iframe so Streamlit never destroys its DOM."""
    import json

    steps = [dict(s) for s in _THINKING_STEPS_JS]
    # enrich LLM substream with real passage doc_ids (GPT/DeepSeek thinking feel)
    if passages:
        llm_trace: list[str] = []
        for i, p in enumerate(passages[:5], start=1):
            doc_id = getattr(p, "doc_id", None) or getattr(p, "id", None) or f"passage_{i}"
            score = getattr(p, "score", 0.0)
            llm_trace.append(f"fonte {i:02d} · {doc_id}  ({score:.2f})")
        while len(llm_trace) < 5:
            llm_trace.append("sintetizando evidências...")
        steps[-1]["substream"] = llm_trace

    steps_json = json.dumps(steps)
    mode = "done" if done else "live"
    details_json = json.dumps(
        {
            "total_ms": total_time_ms,
            "first_token_ms": first_token_ms,
            "tokens": tokens,
        }
    )
    theme_vars = _THINKING_VARS_DARK if theme == "dark" else _THINKING_VARS_LIGHT

    return f"""<!DOCTYPE html>
<html lang="pt-BR"><head><meta charset="utf-8"/>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
<style>
:root {{
{theme_vars}  --accent: oklch(58% 0.19 15);
  --accent-soft: oklch(58% 0.19 15 / 0.14);
  --accent-ring: oklch(58% 0.19 15 / 0.28);
  --ok: oklch(70% 0.14 150);
  --font-body: 'Inter', system-ui, sans-serif;
  --font-mono: 'JetBrains Mono', ui-monospace, monospace;
  --ease: cubic-bezier(.2,.7,.2,1);
}}
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
html, body {{ background: transparent; font-family: var(--font-body); color: var(--text); font-size: 14px; overflow: hidden; }}
body {{ padding: 2px; }}

.card {{
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-left: 3px solid var(--accent);
  border-radius: 10px;
  padding: 14px 16px;
  position: relative;
  overflow: hidden;
  max-width: 680px;
}}
.card::before {{
  content: ""; position: absolute; inset: 0; pointer-events: none;
  background: linear-gradient(110deg, transparent 30%, var(--accent-soft) 50%, transparent 70%);
  background-size: 220% 100%;
  animation: cardSweep 4.2s linear infinite;
  opacity: .55;
}}
@keyframes cardSweep {{
  from {{ background-position: 180% 0; }}
  to   {{ background-position: -80% 0; }}
}}
.card > * {{ position: relative; z-index: 1; }}

.title {{
  font-family: var(--font-mono); font-size: 10.5px; font-weight: 600;
  letter-spacing: .1em; text-transform: uppercase; color: var(--text-faint);
  margin-bottom: 6px; display: flex; align-items: center; gap: 8px;
}}
.title .live {{
  width: 7px; height: 7px; border-radius: 50%; background: var(--accent);
  animation: liveDot 1.4s ease-in-out infinite;
}}
@keyframes liveDot {{
  0%,100% {{ opacity: .5; transform: scale(1); box-shadow: 0 0 0 0 var(--accent-ring); }}
  50%     {{ opacity: 1;  transform: scale(1.3); box-shadow: 0 0 0 6px transparent; }}
}}
.title .stamp {{
  margin-left: auto; color: var(--ok);
}}

.rows {{ display: grid; gap: 4px; }}

.row {{
  display: flex; align-items: center; gap: 10px;
  font-size: 12.5px; color: var(--text-muted);
  padding: 4px 6px; margin-left: -6px;
  border-radius: 6px; position: relative;
}}
.row.active {{
  background: linear-gradient(90deg, transparent 0%, var(--accent-soft) 35%, var(--accent-soft) 65%, transparent 100%);
  background-size: 260% 100%;
  animation: bgSweep 2.4s cubic-bezier(.45,0,.55,1) infinite;
}}
@keyframes bgSweep {{
  from {{ background-position: 130% 0; }}
  to   {{ background-position: -130% 0; }}
}}
.row.pending {{ opacity: .4; }}

.mark {{
  width: 16px; height: 16px; border-radius: 50%;
  display: grid; place-items: center; flex-shrink: 0;
  font-family: var(--font-mono); font-size: 10px; font-weight: 700;
}}
.row.pending .mark {{ border: 1px dashed var(--border-strong); }}
.row.active .mark {{
  border: 2px solid var(--accent-ring);
  border-top-color: var(--accent);
  animation: spin .75s linear infinite;
}}
@keyframes spin {{ to {{ transform: rotate(360deg); }} }}
.row.done .mark {{
  background: oklch(70% 0.14 150 / 0.18);
  color: var(--ok);
  border: 1px solid oklch(70% 0.14 150 / 0.40);
}}
.row.done .mark::before {{ content: "✓"; }}

.lbl {{ color: var(--text); font-weight: 500; flex-shrink: 0; white-space: nowrap; }}
.row.pending .lbl {{ color: var(--text-faint); font-weight: 400; }}

.trace {{
  flex: 1; min-width: 0; height: 16px;
  position: relative; overflow: hidden;
}}
.row:not(.active) .trace {{ display: none; }}
.trace span {{
  position: absolute; inset: 0;
  height: 16px; line-height: 16px;
  font-family: var(--font-mono); font-size: 10.5px;
  color: var(--text-dim);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  opacity: 0; transform: translateY(6px);
  animation: traceRotate 6s infinite;
}}
.trace span::before {{
  content: "›"; margin-right: 5px; color: var(--accent); opacity: .75;
}}
.trace span:nth-child(1) {{ animation-delay: 0s; }}
.trace span:nth-child(2) {{ animation-delay: 1.2s; }}
.trace span:nth-child(3) {{ animation-delay: 2.4s; }}
.trace span:nth-child(4) {{ animation-delay: 3.6s; }}
.trace span:nth-child(5) {{ animation-delay: 4.8s; }}
@keyframes traceRotate {{
  0%   {{ opacity: 0; transform: translateY(6px); }}
  3%   {{ opacity: 1; transform: translateY(0); }}
  17%  {{ opacity: 1; transform: translateY(0); }}
  20%  {{ opacity: 0; transform: translateY(-6px); }}
  100% {{ opacity: 0; transform: translateY(-6px); }}
}}

.detail {{
  font-family: var(--font-mono); font-size: 10.5px;
  color: var(--text-faint); flex-shrink: 0;
  padding: 1px 6px; border-radius: 4px;
  background: var(--surface); border: 1px solid var(--border);
}}
.row.active .detail {{ color: var(--text); border-color: var(--accent-ring); }}
.row.done .detail {{ color: var(--accent); border-color: var(--accent-ring); }}

@media (prefers-reduced-motion: reduce) {{
  .card::before, .row.active, .row.active .mark, .title .live, .trace span {{
    animation: none !important;
  }}
}}
</style></head>
<body>
<div class="card" id="card">
  <div class="title"><span class="live"></span><span id="title-text">Pipeline do agente · streaming</span><span class="stamp" id="stamp"></span></div>
  <div class="rows" id="rows"></div>
</div>
<script>
const STEPS = {steps_json};
const MODE = {mode!r};
const DETAILS = {details_json};

function render(activeIdx, doneSet) {{
  const rows = document.getElementById('rows');
  rows.innerHTML = STEPS.map((s, i) => {{
    let status = 'pending';
    if (doneSet.has(i)) status = 'done';
    else if (i === activeIdx) status = 'active';
    const trace = s.substream.slice(0, 5)
      .map(t => `<span>${{escapeHtml(t)}}</span>`).join('');
    let detail = '';
    if (status === 'done') detail = 'ok';
    if (status === 'active' && i === activeIdx) {{
      const dots = '·'.repeat(1 + (Date.now() / 500 | 0) % 3);
      detail = 'executando' + dots;
    }}
    return `<div class="row ${{status}}">
      <span class="mark"></span>
      <span class="lbl">${{escapeHtml(s.label)}}</span>
      <span class="trace">${{trace}}</span>
      ${{detail ? `<span class="detail">${{detail}}</span>` : ''}}
    </div>`;
  }}).join('');
}}

function escapeHtml(s) {{
  return String(s).replace(/[&<>"']/g, c => ({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[c]));
}}

if (MODE === 'done') {{
  const doneSet = new Set(STEPS.map((_, i) => i));
  render(-1, doneSet);
  document.getElementById('title-text').textContent = 'Pipeline concluído';
  const parts = [];
  if (DETAILS.total_ms) parts.push(`${{(DETAILS.total_ms/1000).toFixed(1)}}s`);
  if (DETAILS.tokens) parts.push(`${{DETAILS.tokens}} tok`);
  if (DETAILS.first_token_ms) parts.push(`1º tok ${{Math.round(DETAILS.first_token_ms)}}ms`);
  document.getElementById('stamp').textContent = parts.join(' · ');
}} else {{
  let active = 0;
  const doneSet = new Set();
  render(active, doneSet);
  // Advance ~1.5s per pre-LLM step, then hold on LLM indefinitely.
  function advance() {{
    if (active < STEPS.length - 1) {{
      doneSet.add(active);
      active += 1;
      render(active, doneSet);
      const wait = (active === STEPS.length - 1) ? 9999999 : (1200 + Math.random() * 800);
      setTimeout(advance, wait);
    }}
  }}
  setTimeout(advance, 1200 + Math.random() * 600);
  // periodic re-render for the ·/·· dot animation
  setInterval(() => render(active, doneSet), 450);
}}
</script>
</body></html>"""


def _completion_pill_html(
    *,
    total_time_ms: float | None,
    first_token_ms: float | None,
    tokens: int | None,
    sources: int,
) -> str:
    """Compact inline pill shown after the thinking iframe is cleared.

    Replaces the previous 'done-state iframe re-mount' — one deterministic
    transition, no animation restart. Uses the same --accent / --ok tokens
    so it automatically adapts to light/dark theme.
    """
    pills: list[str] = []
    if total_time_ms is not None:
        pills.append(
            f"<span class='pill'><span class='k'>⏱</span>"
            f"<span class='v'>{_format_duration_ms(total_time_ms)}</span></span>"
        )
    if first_token_ms:
        pills.append(
            f"<span class='pill'><span class='k'>1º tok</span>"
            f"<span class='v'>{_format_duration_ms(first_token_ms)}</span></span>"
        )
    if tokens:
        pills.append(
            f"<span class='pill'><span class='k'>tokens</span>"
            f"<span class='v'>{tokens}</span></span>"
        )
    pills.append(
        f"<span class='pill'><span class='k'>fontes</span>"
        f"<span class='v'>{sources}</span></span>"
    )
    return (
        "<div class='completion-pill-row'>"
        "<span class='completion-done'>✓ Pipeline concluído</span>"
        + "".join(pills)
        + "</div>"
    )


def _typing_block() -> str:
    return (
        "<div class='typing'>"
        "<div class='typing-label'>"
        "<span class='pulse'></span>"
        "Recuperando passagens · gerando resposta"
        "</div>"
        "<div class='shimmer'></div>"
        "<div class='shimmer s2'></div>"
        "<div class='shimmer s3'></div>"
        "</div>"
    )


def _render_chat_intro() -> str:
    return (
        "<div class='chat-intro'>"
        "<h4>Como funciona</h4>"
        "<p><b>Pergunta</b> livre ou clique em um dos cards abaixo. "
        "O pipeline recupera trechos relevantes de <code>docs/</code> + data cards reais CE/SP "
        "e gera a resposta com citações ao final.</p>"
        "</div>"
    )


def _render_sources_html(passages: list) -> str:
    if not passages:
        return ""
    items: list[str] = []
    for i, p in enumerate(passages, start=1):
        source_path = getattr(p, "source_path", "") or getattr(p, "doc_id", "") or ""
        anchor = getattr(p, "anchor", "") or ""
        section = getattr(p, "section", "") or ""
        doc_id = source_path
        if anchor:
            doc_id = f"{source_path}#{anchor}"
        elif section:
            doc_id = f"{source_path}#{section}"
        if not doc_id:
            doc_id = getattr(p, "id", str(i))
        score = getattr(p, "score", 0.0)
        items.append(
            f"<div class='source'>"
            f"<span class='n'>{i:02d}</span>"
            f"<span class='path'>{html.escape(str(doc_id))}</span>"
            f"<span class='score'>{score:.2f}</span>"
            f"</div>"
        )
    return (
        "<div class='sources'>"
        f"<div class='sources-head'>Fontes"
        f"<span class='count'>{len(passages)}</span></div>"
        f"<div class='sources-list'>{''.join(items)}</div>"
        "</div>"
    )


def _format_duration_ms(value_ms: float | int | None) -> str:
    if value_ms is None:
        return "n/d"
    seconds = max(float(value_ms) / 1000.0, 0.0)
    if seconds < 60:
        return f"{seconds:.1f} s"
    minutes = int(seconds // 60)
    remainder = seconds - (minutes * 60)
    return f"{minutes} min {remainder:.0f} s"


def _format_metadata(meta: dict[str, Any]) -> str:
    total_tokens = int(meta.get("prompt_tokens", 0)) + int(meta.get("completion_tokens", 0))
    tok_cls = "ok" if total_tokens < 2000 else ("warn" if total_tokens < 4000 else "crit")
    first_tok = meta.get("first_token_ms")
    first_tok_pill = (
        f"<span class='pill'><span class='k'>1º tok</span>"
        f"<span class='v'>{_format_duration_ms(first_tok)}</span></span>"
        if first_tok
        else ""
    )
    cache_pill = (
        f"<span class='pill'><span class='k'>cache</span>"
        f"<span class='v'>{'hit' if meta.get('cache_hit') else 'miss'}</span></span>"
        if "cache_hit" in meta
        else ""
    )
    return (
        "<div class='meta-row'>"
        f"<span class='pill'><span class='k'>intent</span>"
        f"<span class='v'>{meta.get('intent', '?')}</span></span>"
        f"<span class='pill {tok_cls}'><span class='k'>tokens</span>"
        f"<span class='v'>{total_tokens}</span></span>"
        f"<span class='pill'><span class='k'>⏱</span>"
        f"<span class='v'>{_format_duration_ms(meta.get('latency_ms', 0))}</span></span>"
        f"{first_tok_pill}"
        f"{cache_pill}"
        f"<span class='pill'><span class='k'>fontes</span>"
        f"<span class='v'>{meta.get('sources', 0)}</span></span>"
        "</div>"
    )


def _history_for_llm(history: list[dict[str, Any]]) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for turn in history[-8:]:
        if turn.get("role") in {"user", "assistant"}:
            out.append({"role": turn["role"], "content": str(turn.get("content", ""))})
    return out


def _render_feedback_row(st: Any, turn: dict[str, Any], *, idx: int) -> None:
    q_hash = turn.get("q_hash")
    if not q_hash or turn.get("feedback_sent"):
        return
    config = st.session_state.get("rag_config")
    if config is None:
        return
    st.markdown("<div class='fb-row-wrap'>", unsafe_allow_html=True)
    cols = st.columns([1, 1, 1, 1, 10])
    with cols[0]:
        if st.button("↑", key=f"fb_up_{idx}", help="Útil"):
            if log_feedback(config.feedback_path, question_hash=q_hash, rating="up"):
                turn["feedback_sent"] = True
                st.toast("Obrigado pelo feedback!", icon="✨")
            else:
                st.toast("Não foi possível registrar o feedback.", icon="⚠")
    with cols[1]:
        if st.button("↓", key=f"fb_down_{idx}", help="Não útil"):
            if log_feedback(config.feedback_path, question_hash=q_hash, rating="down"):
                turn["feedback_sent"] = True
                st.toast("Feedback registrado para melhoria.", icon="🛠")
            else:
                st.toast("Não foi possível registrar o feedback.", icon="⚠")
    with cols[2]:
        st.button("⧉", key=f"fb_copy_{idx}", help="Copiar")
    with cols[3]:
        st.button("↻", key=f"fb_retry_{idx}", help="Reexecutar")
    st.markdown("</div>", unsafe_allow_html=True)
