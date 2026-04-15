"""Aba '💬 Assistente ENEL' — chat RAG embarcado no dashboard.

UX:
- Saudação inteligente com hora do dia + último contexto do dashboard.
- 8 perguntas pré-existentes em chips clicáveis.
- Streaming via `st.write_stream`.
- Citações clicáveis renderizadas como lista de fontes.
- Indicadores de provider, tokens, intent.
- Feedback 👍/👎 por resposta em `data/rag/feedback.csv`.
- Estado persistido em `st.session_state["chat_history"]`.
"""

from __future__ import annotations

from typing import Any

from apps.streamlit.components.narrative import LayerNarrative, layer_intro
from src.rag.config import load_rag_config
from src.rag.orchestrator import RagOrchestrator, format_citations, greeting_response
from src.rag.prompts import SUGGESTED_QUESTIONS
from src.rag.retriever import check_stub_corpus
from src.rag.telemetry import hash_question, log_feedback


def _build_orchestrator(st: Any) -> RagOrchestrator:
    if "rag_orchestrator" not in st.session_state:
        config = load_rag_config()
        st.session_state["rag_config"] = config
        st.session_state["rag_orchestrator"] = RagOrchestrator(config)
    return st.session_state["rag_orchestrator"]


def _tokens_badge_color(tokens: int) -> str:
    if tokens < 2000:
        return "#00813E"
    if tokens < 4000:
        return "#F7941D"
    return "#E4002B"


def render(st: Any, *, theme: str = "light", context_hint: str | None = None) -> None:
    del theme
    layer_intro(
        st,
        LayerNarrative(
            icon="💬",
            title="Assistente ENEL",
            question="O que você precisa entender sobre a plataforma analítica?",
            method=(
                "RAG open-source CPU-only: MiniLM PT-BR + ChromaDB + LLM local "
                "(GGUF quantizado). Respostas com citações para todos os arquivos em `docs/`."
            ),
            action=(
                "Use os chips abaixo para começar, ou digite sua pergunta. "
                "As fontes citadas viram links clicáveis ao final de cada resposta."
            ),
        ),
    )

    orch = _build_orchestrator(st)
    config = st.session_state["rag_config"]

    corpus_ready = check_stub_corpus(config.chromadb_path)
    provider_name = getattr(orch.provider, "name", "stub")
    model_name = getattr(orch.provider, "model", "?")

    col_left, col_right = st.columns([3, 1])
    with col_right:
        st.markdown(
            f"<div class='enel-card' style='padding:0.8rem;font-size:0.85rem;'>"
            f"<div><strong>Provedor</strong>: <code>{provider_name}</code></div>"
            f"<div><strong>Modelo</strong>: <code>{model_name}</code></div>"
            f"<div><strong>Índice</strong>: "
            f"{'✅ pronto' if corpus_ready else '⚠️ vazio'}</div>"
            "</div>",
            unsafe_allow_html=True,
        )
        if not corpus_ready:
            st.caption(
                "Rode `python scripts/build_rag_corpus.py --rebuild` "
                "para indexar `docs/`."
            )
        if provider_name == "stub":
            st.caption(
                "Sem LLM ativo — respostas em modo stub (apenas contexto). "
                "Rode `python scripts/build_rag_corpus.py --download-model` "
                "e defina `RAG_PROVIDER=llama_cpp`."
            )

    with col_left:
        if "chat_history" not in st.session_state:
            st.session_state["chat_history"] = []
            st.session_state["chat_first_open"] = True

        if st.session_state.get("chat_first_open"):
            st.chat_message("assistant", avatar="⚡").markdown(
                greeting_response(context_hint)
            )
            st.session_state["chat_first_open"] = False

        st.markdown("**Sugestões rápidas:**")
        chip_cols = st.columns(4)
        for idx, (q, _tag) in enumerate(SUGGESTED_QUESTIONS):
            with chip_cols[idx % 4]:
                if st.button(q, key=f"chip_{idx}", use_container_width=True):
                    st.session_state["pending_question"] = q

        for i, turn in enumerate(st.session_state["chat_history"]):
            avatar = "⚡" if turn["role"] == "assistant" else "🧑"
            with st.chat_message(turn["role"], avatar=avatar):
                st.markdown(turn["content"])
                if turn["role"] == "assistant":
                    _render_feedback_row(st, turn, idx=i)

        pending = st.session_state.pop("pending_question", None)
        user_input = st.chat_input("Pergunte sobre a plataforma ENEL…") or pending

        if user_input:
            st.session_state["chat_history"].append({"role": "user", "content": user_input})
            with st.chat_message("user", avatar="🧑"):
                st.markdown(user_input)

            with st.chat_message("assistant", avatar="⚡"):
                with st.spinner("Pensando com base nos documentos…"):
                    resp = orch.answer(
                        user_input,
                        history=_history_for_llm(st.session_state["chat_history"]),
                        context_hint=context_hint,
                    )
                full_text = resp.text + format_citations(resp.passages)
                st.markdown(full_text)

                total_tokens = resp.prompt_tokens + resp.completion_tokens
                color = _tokens_badge_color(total_tokens)
                st.markdown(
                    f"<div style='margin-top:0.35rem;font-size:0.78rem;color:#6B7680;'>"
                    f"intent: <code>{resp.intent}</code> · "
                    f"<span style='color:{color};font-weight:600;'>"
                    f"{total_tokens} tokens</span> · "
                    f"{resp.latency_ms:.0f} ms · "
                    f"{len(resp.passages)} fontes"
                    "</div>",
                    unsafe_allow_html=True,
                )

                assistant_turn = {
                    "role": "assistant",
                    "content": full_text,
                    "q_hash": hash_question(user_input),
                }
                st.session_state["chat_history"].append(assistant_turn)
                _render_feedback_row(
                    st, assistant_turn, idx=len(st.session_state["chat_history"]) - 1
                )

        if st.session_state["chat_history"]:
            if st.button("🧹 Limpar conversa", use_container_width=False):
                st.session_state["chat_history"] = []
                st.session_state["chat_first_open"] = True
                st.rerun()


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
