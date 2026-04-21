"""Narrative helpers for self-explanatory dashboard layers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import pandas as pd


@dataclass(frozen=True, slots=True)
class LayerNarrative:
    title: str
    question: str
    method: str
    action: str
    icon: str = "📊"


def build_intro_markdown(narrative: LayerNarrative) -> str:
    """Return the compact layer header.

    Keeps the original contract strings — ``Pergunta de negócio``, ``Como lemos``
    and ``Próximo passo`` — so downstream tests and screen-readers still see the
    same semantic anchors.
    """
    return f"""
<section class="enel-tab-header" aria-label="Contexto da camada {narrative.title}">
  <div class="enel-tab-icon" aria-hidden="true">{narrative.icon}</div>
  <div class="enel-tab-copy">
    <h1>{narrative.title}</h1>
    <p><strong>Pergunta de negócio:</strong> {narrative.question}</p>
    <p><strong>Como lemos:</strong> {narrative.method}</p>
    <p><strong>Próximo passo:</strong> {narrative.action}</p>
  </div>
</section>
"""


def layer_intro(st: Any, narrative: LayerNarrative) -> None:  # pragma: no cover
    """Render a layer intro using Streamlit."""
    st.markdown(build_intro_markdown(narrative), unsafe_allow_html=True)


def empty_state_markdown(
    *,
    title: str = "Nenhum registro para estes filtros",
    detail: str = "Relaxe período, região ou causa para recuperar sinal estatístico.",
) -> str:
    return f"""
<div class="enel-empty" role="status">
  <h3>🔍 {title}</h3>
  <p>{detail}</p>
</div>
"""


def render_empty_state(st: Any, **kwargs: str) -> None:  # pragma: no cover
    st.markdown(empty_state_markdown(**kwargs), unsafe_allow_html=True)


def dataframe_to_csv_bytes(frame: pd.DataFrame) -> bytes:
    """Serialize a dataframe with stable UTF-8 BOM for Excel-friendly exports."""
    return frame.to_csv(index=False).encode("utf-8-sig")


def export_filename(section: str, *, suffix: str = "csv") -> str:
    stamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    safe = "".join(ch if ch.isalnum() else "_" for ch in section.lower()).strip("_")
    return f"enel_{safe}_{stamp}.{suffix}"


def download_dataframe(  # pragma: no cover - thin Streamlit wrapper.
    st: Any,
    label: str,
    frame: pd.DataFrame,
    *,
    section: str,
) -> None:
    st.download_button(
        label,
        data=dataframe_to_csv_bytes(frame),
        file_name=export_filename(section),
        mime="text/csv",
        use_container_width=True,
        disabled=frame.empty,
    )
