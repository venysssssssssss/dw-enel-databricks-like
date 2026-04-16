"""Aba '💬 Assistente ENEL' — chat RAG embarcado no dashboard.

UX:
- Layout full-width com hero state, chips categorizados e bolhas ENEL-themed.
- Streaming token-a-token via `st.write_stream` (stream_answer do orchestrator).
- Citações como expander "Fontes (N)" ao final.
- Indicadores de provider, modelo, tokens, intent e latência.
- Feedback 👍/👎 por resposta em `data/rag/feedback.csv`.
- Greeting dinâmica com hora + último contexto do dashboard.
"""

from __future__ import annotations

import time
from typing import Any

from apps.streamlit.components.narrative import LayerNarrative, layer_intro
from src.rag.config import load_rag_config
from src.rag.orchestrator import (
    RagOrchestrator,
    classify_intent,
    format_citations,
    greeting_response,
)
from src.rag.prompts import SUGGESTED_QUESTIONS
from src.rag.retriever import check_stub_corpus, route_doc_types
from src.rag.safety import OUT_OF_SCOPE_MESSAGE, check_input, is_out_of_scope
from src.rag.telemetry import hash_question, log_feedback

_CHIP_CATEGORIES: dict[str, str] = {
    "business": "📘 Regras",
    "ml": "🧠 Modelos",
    "viz": "📊 Dashboard",
    "architecture": "🏗 Arquitetura",
    "sprint": "🚀 Sprints",
    "data": "📈 Dados",
}

_DATA_QUESTIONS: list[tuple[str, str]] = [
    ("Quantas reclamações temos no total (CE + SP)?", "data"),
    ("Quais os top 5 assuntos de reclamação?", "data"),
    ("Qual a causa-raiz mais frequente?", "data"),
    ("Como foi a evolução mensal de reclamações?", "data"),
]


_CHAT_CSS = """
<style>
/* ===== Chat hero (gradient ENEL) ===== */
.chat-hero {
  position: relative;
  overflow: hidden;
  background:
    linear-gradient(135deg,
      rgba(135,10,60,0.98) 0%,
      rgba(200,16,46,0.96) 58%,
      rgba(228,0,43,0.94) 100%);
  color: #fff;
  padding: 1.45rem 1.7rem;
  border-radius: var(--enel-radius-lg, 22px);
  margin-bottom: 1rem;
  box-shadow: 0 18px 45px rgba(15, 76, 129, 0.22);
  animation: chatHeroIn 360ms cubic-bezier(.2,.8,.2,1) both;
}
.chat-hero::after {
  content: ""; position: absolute; inset: 0;
  background-image:
    linear-gradient(rgba(255,255,255,0.05) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255,255,255,0.05) 1px, transparent 1px);
  background-size: 24px 24px;
  pointer-events: none; opacity: 0.55;
}
.chat-hero h3 {
  position: relative; z-index: 1;
  margin: 0 0 0.4rem 0;
  font-size: 1.35rem;
  font-weight: 800;
  letter-spacing: 0;
  color: #fff;
}
.chat-hero p {
  position: relative; z-index: 1;
  margin: 0;
  opacity: 0.94;
  font-size: 0.95rem;
  line-height: 1.5;
  max-width: 720px;
}
@keyframes chatHeroIn {
  from { opacity: 0; transform: translateY(8px); }
  to   { opacity: 1; transform: translateY(0); }
}

/* ===== Status panel (glass) ===== */
.chat-status {
  background: var(--enel-glass-bg, rgba(255,255,255,0.72));
  border: 1px solid var(--enel-glass-border, rgba(15,76,129,0.10));
  border-radius: var(--enel-radius-md, 14px);
  padding: 1rem 1.1rem;
  font-size: 0.85rem;
  line-height: 1.55;
  box-shadow: var(--enel-shadow, 0 18px 45px rgba(15,76,129,0.10));
  backdrop-filter: blur(14px) saturate(120%);
  -webkit-backdrop-filter: blur(14px) saturate(120%);
}
.chat-status .label {
  color: var(--enel-muted, #6B7680);
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  font-size: 0.72rem;
}
.chat-status .value {
  color: var(--enel-text, #141B25);
  font-family: 'JetBrains Mono', 'Menlo', monospace;
  font-variant-numeric: tabular-nums;
  font-weight: 600;
}
.chat-status .status-ok   { color: #1E7B55; font-weight: 700; }
.chat-status .status-warn { color: #9A5800; font-weight: 700; }
.chat-status .status-crit { color: #E4002B; font-weight: 700; }

/* ===== Suggested chip section ===== */
.chat-chip-label {
  color: var(--enel-muted, #6B7680);
  font-weight: 700;
  font-size: 0.78rem;
  margin: 0.6rem 0 0.3rem 0;
  letter-spacing: 0.05em;
  text-transform: uppercase;
}

/* ===== Assistant metadata pills ===== */
.chat-metadata {
  color: var(--enel-muted, #6B7680);
  font-size: 0.74rem;
  margin-top: 0.5rem;
  display: flex; gap: 0.5rem; flex-wrap: wrap; align-items: center;
}
.chat-metadata .pill {
  padding: 0.22rem 0.6rem;
  border-radius: 999px;
  background: var(--enel-glass-bg, rgba(247,249,252,0.85));
  border: 1px solid var(--enel-border, #E6ECF2);
  font-weight: 600;
  font-feature-settings: 'tnum';
  transition: transform 140ms ease, border-color 140ms ease;
}
.chat-metadata .pill:hover {
  transform: translateY(-1px);
  border-color: var(--enel-secondary, #C8102E);
}
.chat-metadata .pill code {
  background: transparent; padding: 0;
  color: var(--enel-primary, #870A3C);
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.74rem;
}
.chat-metadata .pill.ok   {
  background: rgba(30,123,85,0.12);
  border-color: rgba(30,123,85,0.34);
  color: #1E7B55;
}
.chat-metadata .pill.warn {
  background: rgba(247,148,29,0.12);
  border-color: rgba(247,148,29,0.35);
  color: #B86008;
}
.chat-metadata .pill.crit {
  background: rgba(228,0,43,0.10);
  border-color: rgba(228,0,43,0.30);
  color: #B8001F;
}

/* ===== Animated typing indicator (3 dots) ===== */
.chat-typing {
  display: inline-flex; align-items: center; gap: 0.55rem;
  color: var(--enel-primary, #870A3C);
  font-weight: 600;
  font-size: 0.9rem;
  padding: 0.4rem 0.8rem;
  background: var(--enel-glass-bg, rgba(255,255,255,0.7));
  border: 1px solid var(--enel-glass-border, rgba(15,76,129,0.12));
  border-radius: 999px;
  backdrop-filter: blur(10px);
  width: fit-content;
}
.chat-typing-dots {
  display: inline-flex; gap: 0.22rem; align-items: center;
}
.chat-typing-dots span {
  width: 6px; height: 6px; border-radius: 50%;
  background: var(--enel-secondary, #C8102E);
  animation: typingPulse 1.1s ease-in-out infinite;
}
.chat-typing-dots span:nth-child(2) { animation-delay: 0.18s; }
.chat-typing-dots span:nth-child(3) { animation-delay: 0.36s; }
@keyframes typingPulse {
  0%, 80%, 100% { transform: scale(0.6); opacity: 0.45; }
  40%           { transform: scale(1.0); opacity: 1; }
}

/* ===== Sources expander styling ===== */
.chat-sources summary {
  cursor: pointer;
  color: var(--enel-primary, #870A3C);
  font-weight: 700;
  font-size: 0.86rem;
  padding: 0.4rem 0;
}
.chat-sources ul {
  margin: 0.3rem 0 0.2rem 1.1rem;
  padding: 0;
  font-size: 0.82rem;
  line-height: 1.6;
}

/* ===== st.chat_message bubble polish ===== */
[data-testid="stChatMessage"] {
  background: var(--enel-glass-bg, rgba(255,255,255,0.72)) !important;
  border: 1px solid var(--enel-glass-border, rgba(15,76,129,0.08))
    !important;
  border-radius: var(--enel-radius-md, 14px) !important;
  padding: 0.9rem 1.1rem !important;
  box-shadow: 0 4px 14px rgba(15, 76, 129, 0.06);
  backdrop-filter: blur(10px);
  color: var(--enel-text, #1D1F24) !important;
  margin-bottom: 0.6rem;
  animation: bubbleIn 220ms cubic-bezier(.2,.8,.2,1) both;
}
@keyframes bubbleIn {
  from { opacity: 0; transform: translateY(4px); }
  to   { opacity: 1; transform: translateY(0); }
}

/* ===== Chat input refinement ===== */
[data-testid="stChatInput"] textarea {
  border-radius: 14px !important;
  border-color: var(--enel-border, #DCE7F1) !important;
  font-family: 'Inter', sans-serif !important;
}
[data-testid="stChatInput"] textarea:focus {
  border-color: var(--enel-secondary, #C8102E) !important;
  box-shadow: 0 0 0 3px rgba(200,16,46,0.18) !important;
}
</style>
"""


def render(st: Any, *, theme: str = "light", context_hint: str | None = None) -> None:
    del theme
    st.markdown(_CHAT_CSS, unsafe_allow_html=True)

    layer_intro(
        st,
        LayerNarrative(
            icon="💬",
            title="Assistente ENEL",
            question="O que você precisa entender sobre a plataforma analítica?",
            method=(
                "RAG open-source CPU-only: ChromaDB + Qwen2.5-3B-Instruct Q4_K_M (GGUF). "
                "Corpus indexa `docs/**` + data cards reais CE/SP (184.690 ordens do silver)."
            ),
            action=(
                "Use os chips por categoria ou digite sua pergunta. "
                "As respostas trazem citações clicáveis ao final."
            ),
        ),
    )

    orch = _build_orchestrator(st)
    config = st.session_state["rag_config"]
    corpus_ready = check_stub_corpus(config.chromadb_path)
    provider_name = getattr(orch.provider, "name", "stub")
    model_name = getattr(orch.provider, "model", "?")

    col_chat, col_side = st.columns([2.4, 1])

    with col_side:
        _render_status_panel(st, provider_name, model_name, corpus_ready)
        _render_suggested_panel(st)

    with col_chat:
        _render_chat_area(st, orch, config, context_hint)


def _build_orchestrator(st: Any) -> RagOrchestrator:
    if "rag_orchestrator" not in st.session_state:
        config = load_rag_config()
        st.session_state["rag_config"] = config
        with st.spinner("Carregando modelo local (Qwen2.5-3B)…"):
            st.session_state["rag_orchestrator"] = RagOrchestrator(config)
    return st.session_state["rag_orchestrator"]


def _render_status_panel(
    st: Any, provider: str, model: str, corpus_ready: bool
) -> None:
    corpus_html = (
        "<span class='status-ok'>✅ pronto</span>" if corpus_ready
        else "<span class='status-warn'>⚠️ vazio</span>"
    )
    provider_html = (
        "<span class='status-ok'>🔒 local</span>" if provider == "llama_cpp"
        else "<span class='status-warn'>stub</span>"
    )
    st.markdown(
        f"""
        <div class='chat-status'>
          <div class='label'>Modelo</div>
          <div class='value'>{model}</div>
          <div class='label' style='margin-top:0.55rem;'>Provider</div>
          <div class='value'>{provider} · {provider_html}</div>
          <div class='label' style='margin-top:0.55rem;'>Índice</div>
          <div class='value'>{corpus_html}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if not corpus_ready:
        st.caption(
            "Rode `python scripts/build_rag_corpus.py --rebuild` para indexar."
        )
    if provider == "stub":
        st.caption(
            "Sem LLM ativo. Instale `llama-cpp-python` e baixe o GGUF via "
            "`scripts/build_rag_corpus.py --download-model`."
        )


def _render_suggested_panel(st: Any) -> None:
    st.markdown(
        "<div class='chat-chip-label'>Comece por aqui:</div>",
        unsafe_allow_html=True,
    )
    all_questions: list[tuple[str, str]] = list(SUGGESTED_QUESTIONS) + _DATA_QUESTIONS
    by_cat: dict[str, list[str]] = {}
    for q, tag in all_questions:
        by_cat.setdefault(tag, []).append(q)

    for tag, items in by_cat.items():
        label = _CHIP_CATEGORIES.get(tag, tag)
        with st.expander(f"{label} ({len(items)})", expanded=(tag == "data")):
            for i, q in enumerate(items):
                if st.button(q, key=f"chip_{tag}_{i}", use_container_width=True):
                    st.session_state["pending_question"] = q
                    st.rerun()


def _render_chat_area(
    st: Any,
    orch: RagOrchestrator,
    config: Any,
    context_hint: str | None,
) -> None:
    if "chat_history" not in st.session_state:
        st.session_state["chat_history"] = []
        st.session_state["chat_first_open"] = True

    if st.session_state.get("chat_first_open") and not st.session_state["chat_history"]:
        hero_msg = greeting_response(context_hint)
        st.markdown(
            f"""
            <div class='chat-hero'>
              <h3>⚡ Assistente ENEL</h3>
              <p>{hero_msg}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    for i, turn in enumerate(st.session_state["chat_history"]):
        avatar = "⚡" if turn["role"] == "assistant" else "🧑"
        with st.chat_message(turn["role"], avatar=avatar):
            st.markdown(turn["content"], unsafe_allow_html=True)
            if turn["role"] == "assistant":
                meta = turn.get("meta")
                if meta:
                    st.markdown(_format_metadata(meta), unsafe_allow_html=True)
                _render_feedback_row(st, turn, idx=i)

    pending = st.session_state.pop("pending_question", None)
    user_input = st.chat_input("Pergunte sobre a plataforma ENEL…") or pending
    if user_input:
        _handle_user_turn(st, orch, config, user_input, context_hint)

    bottom_cols = st.columns([1, 1, 4])
    with bottom_cols[0]:
        if st.session_state["chat_history"] and st.button(
            "🧹 Limpar", use_container_width=True
        ):
            st.session_state["chat_history"] = []
            st.session_state["chat_first_open"] = True
            st.rerun()


def _handle_user_turn(
    st: Any,
    orch: RagOrchestrator,
    config: Any,
    user_input: str,
    context_hint: str | None,
) -> None:
    st.session_state["chat_first_open"] = False
    st.session_state["chat_history"].append({"role": "user", "content": user_input})
    with st.chat_message("user", avatar="🧑"):
        st.markdown(user_input)

    history = _history_for_llm(st.session_state["chat_history"])

    with st.chat_message("assistant", avatar="⚡"):
        meta, full_text = _stream_answer(st, orch, config, user_input, history, context_hint)
        if meta:
            st.markdown(_format_metadata(meta), unsafe_allow_html=True)

    turn = {
        "role": "assistant",
        "content": full_text,
        "meta": meta,
        "q_hash": hash_question(user_input),
    }
    st.session_state["chat_history"].append(turn)
    st.rerun()


def _stream_answer(
    st: Any,
    orch: RagOrchestrator,
    config: Any,
    question: str,
    history: list[dict[str, str]],
    context_hint: str | None,
) -> tuple[dict[str, Any] | None, str]:
    """Executa o pipeline RAG emitindo tokens em streaming com st.write_stream.

    Retorna (meta_dict, texto_com_citacoes). meta contém intent, tokens, latência.
    """

    start = time.perf_counter()

    check = check_input(question)
    if not check.allowed:
        st.warning(check.reason or "Pergunta inválida.")
        return None, check.reason or "Pergunta inválida."

    intent = classify_intent(check.sanitized)
    if intent in {"saudacao", "cortesia"}:
        text = greeting_response(context_hint)
        st.markdown(text)
        elapsed = (time.perf_counter() - start) * 1000
        return {
            "intent": intent,
            "prompt_tokens": 0,
            "completion_tokens": len(text) // 4,
            "latency_ms": elapsed,
            "sources": 0,
        }, text

    try:
        passages = orch.retriever.top_passages(
            check.sanitized,
            top_n=config.rerank_top_n,
            doc_types=route_doc_types(check.sanitized),
        )
    except (FileNotFoundError, RuntimeError) as exc:
        msg = (
            "Índice RAG não disponível. Rode "
            "`python scripts/build_rag_corpus.py --rebuild`.\n\n"
            f"_{exc}_"
        )
        st.warning(msg)
        return None, msg

    if is_out_of_scope(passages, config.similarity_threshold):
        st.info(OUT_OF_SCOPE_MESSAGE)
        return None, OUT_OF_SCOPE_MESSAGE

    passages = orch._enforce_budget(passages)  # noqa: SLF001 (reuso intencional)
    from src.rag.prompts import build_messages

    messages = build_messages(
        question=check.sanitized, passages=passages, history=history
    )

    placeholder = st.empty()
    typing_slot = st.empty()
    typing_slot.markdown(
        "<div class='chat-typing'>"
        "<span>⚡ Assistente ENEL pensando</span>"
        "<span class='chat-typing-dots'><span></span><span></span><span></span></span>"
        "</div>",
        unsafe_allow_html=True,
    )

    accumulated: list[str] = []
    first_token_ms: float | None = None
    for chunk in orch.provider.stream(
        messages,
        max_tokens=min(640, config.max_turn_tokens // 2),
        temperature=config.temperature,
        top_p=config.top_p,
    ):
        if first_token_ms is None:
            first_token_ms = (time.perf_counter() - start) * 1000
            typing_slot.empty()
        accumulated.append(chunk)
        placeholder.markdown("".join(accumulated) + "▌")

    body = "".join(accumulated).strip()
    citations_md = format_citations(passages)
    full = body + citations_md
    placeholder.markdown(full, unsafe_allow_html=True)

    elapsed = (time.perf_counter() - start) * 1000
    return {
        "intent": intent,
        "prompt_tokens": sum(len(m.get("content", "")) // 4 for m in messages),
        "completion_tokens": len(body) // 4,
        "latency_ms": elapsed,
        "first_token_ms": first_token_ms or elapsed,
        "sources": len(passages),
    }, full


def _format_metadata(meta: dict[str, Any]) -> str:
    total_tokens = int(meta.get("prompt_tokens", 0)) + int(meta.get("completion_tokens", 0))
    cls = "ok" if total_tokens < 2000 else ("warn" if total_tokens < 4000 else "crit")
    first_tok = meta.get("first_token_ms")
    first_tok_html = (
        f"<span class='pill'>⚡ {first_tok:.0f} ms (1º token)</span>"
        if first_tok else ""
    )
    return (
        "<div class='chat-metadata'>"
        f"<span class='pill'>intent: <code>{meta.get('intent', '?')}</code></span>"
        f"<span class='pill {cls}'>{total_tokens} tokens</span>"
        f"<span class='pill'>⏱ {meta.get('latency_ms', 0):.0f} ms total</span>"
        f"{first_tok_html}"
        f"<span class='pill'>📎 {meta.get('sources', 0)} fontes</span>"
        "</div>"
    )


def _history_for_llm(history: list[dict[str, Any]]) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for turn in history[-8:]:
        if turn.get("role") in {"user", "assistant"}:
            content = str(turn.get("content", "")).split("\n\n---\n**Fontes:**")[0]
            out.append({"role": turn["role"], "content": content})
    return out


def _render_feedback_row(st: Any, turn: dict[str, Any], *, idx: int) -> None:
    q_hash = turn.get("q_hash")
    if not q_hash or turn.get("feedback_sent"):
        return
    config = st.session_state.get("rag_config")
    if config is None:
        return
    cols = st.columns([1, 1, 8])
    with cols[0]:
        if st.button("👍", key=f"fb_up_{idx}"):
            log_feedback(config.feedback_path, question_hash=q_hash, rating="up")
            turn["feedback_sent"] = True
            st.toast("Obrigado pelo feedback!", icon="✨")
    with cols[1]:
        if st.button("👎", key=f"fb_down_{idx}"):
            log_feedback(config.feedback_path, question_hash=q_hash, rating="down")
            turn["feedback_sent"] = True
            st.toast("Feedback registrado para melhoria.", icon="🛠")
