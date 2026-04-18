"""Premium UI helpers — story blocks, insight callouts, DOM pareto, health cards.

These components absorb the best of the `MIS BI Aconchegante` refactor and
re-express it over the graphite oklch design system already shipped in
`apps.streamlit.theme`.  They return pre-rendered HTML fragments so callers can
compose them with any existing layout primitive (st.markdown, st.columns, etc.).

All helpers are pure-Python (no JS, no network) and emit accessible markup:
semantic landmarks, aria labels, and theme-aware colors via CSS variables.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from html import escape
from typing import Any, Iterable, Literal, Sequence

HealthStatus = Literal["ok", "warn", "crit"]
KPIIntent = Literal["neutral", "up_bad", "up_good", "down_bad", "down_good"]


# ───────────────────────── Story block ─────────────────────────

@dataclass(frozen=True, slots=True)
class StoryBlock:
    lead: str
    body: str
    icon: str = "?"
    steps: Sequence[str] = field(default_factory=tuple)


def story_block_markdown(story: StoryBlock) -> str:
    steps_html = ""
    if story.steps:
        items = "".join(
            f'<div class="enel-story-step"><span class="n">{i}</span>{escape(step)}</div>'
            for i, step in enumerate(story.steps, start=1)
        )
        steps_html = f'<div class="enel-story-steps">{items}</div>'
    return (
        '<section class="enel-story" aria-label="Contexto da tela">'
        f'<div class="enel-story-icon" aria-hidden="true">{escape(story.icon)}</div>'
        '<div class="enel-story-body">'
        f'<span class="enel-story-lead">{escape(story.lead)}</span>'
        f"{story.body}"  # body may contain vetted <b> tags — caller's responsibility
        f"{steps_html}"
        "</div>"
        "</section>"
    )


def render_story(st: Any, story: StoryBlock) -> None:  # pragma: no cover
    st.markdown(story_block_markdown(story), unsafe_allow_html=True)


# ───────────────────────── Insight callout ─────────────────────────

def insight_markdown(body: str, *, label: str = "Insight") -> str:
    return (
        '<div class="enel-insight" role="note">'
        f'<span class="label">{escape(label)}</span>{body}'
        "</div>"
    )


def render_insight(st: Any, body: str, *, label: str = "Insight") -> None:  # pragma: no cover
    st.markdown(insight_markdown(body, label=label), unsafe_allow_html=True)


# ───────────────────────── KPI dominant ─────────────────────────

@dataclass(frozen=True, slots=True)
class KPI:
    label: str
    value: str
    tag: str = ""
    delta: str = ""
    delta_intent: KPIIntent = "neutral"
    dominant: bool = False


def _delta_class(intent: KPIIntent) -> str:
    return {
        "up_bad": "d-up",
        "down_good": "d-dn",
        "up_good": "d-dn",
        "down_bad": "d-up",
        "neutral": "",
    }.get(intent, "")


def kpi_card_markdown(kpi: KPI) -> str:
    tag_html = f'<div class="enel-kpi-tag">{escape(kpi.tag)}</div>' if kpi.tag else ""
    delta_html = ""
    if kpi.delta:
        cls = _delta_class(kpi.delta_intent)
        delta_html = f'<span class="{cls}">{escape(kpi.delta)}</span>'
    dominant_cls = " is-dominant" if kpi.dominant else ""
    return (
        f'<div class="enel-kpi{dominant_cls}">'
        f'<div class="enel-kpi-head">'
        f'<div class="enel-kpi-label">{escape(kpi.label)}</div>{tag_html}'
        "</div>"
        f'<div class="enel-kpi-val">{escape(kpi.value)}</div>'
        f'<div class="enel-kpi-sub">{delta_html}</div>'
        "</div>"
    )


def kpi_strip_markdown(kpis: Sequence[KPI]) -> str:
    if not kpis:
        return ""
    inner = "".join(kpi_card_markdown(k) for k in kpis)
    return f'<div class="enel-kpis" role="list">{inner}</div>'


def render_kpi_strip(st: Any, kpis: Sequence[KPI]) -> None:  # pragma: no cover
    st.markdown(kpi_strip_markdown(kpis), unsafe_allow_html=True)


# ───────────────────────── DOM Pareto ─────────────────────────

@dataclass(frozen=True, slots=True)
class ParetoItem:
    name: str
    value: float
    pct: float | None = None  # if None, auto-computed against sum


def pareto_markdown(
    items: Sequence[ParetoItem],
    *,
    highlight_first: bool = True,
    locale_decimal: str = ",",
    locale_thousands: str = ".",
) -> str:
    if not items:
        return ""
    max_v = max((it.value for it in items), default=0.0)
    total = sum(it.value for it in items)
    rows: list[str] = []

    def fmt_int(v: float) -> str:
        s = f"{int(round(v)):,}"
        return (
            s.replace(",", "§").replace(".", locale_decimal).replace("§", locale_thousands)
        )

    for idx, it in enumerate(items):
        width = (it.value / max_v * 100.0) if max_v else 0.0
        pct = it.pct if it.pct is not None else (it.value / total * 100.0 if total else 0.0)
        active = " is-active" if highlight_first and idx == 0 else ""
        rows.append(
            f'<div class="enel-pareto-row{active}" title="{escape(it.name)}">'
            f'<div class="enel-pareto-name">{escape(it.name)}</div>'
            f'<div class="enel-pareto-bar"><div class="enel-pareto-fill" style="width:{width:.1f}%"></div></div>'
            f'<div class="enel-pareto-val">{fmt_int(it.value)}</div>'
            f'<div class="enel-pareto-pct">{pct:.1f}%</div>'
            "</div>"
        )
    return f'<div class="enel-pareto" role="list">{"".join(rows)}</div>'


def render_pareto(st: Any, items: Sequence[ParetoItem], **kwargs: Any) -> None:  # pragma: no cover
    st.markdown(pareto_markdown(items, **kwargs), unsafe_allow_html=True)


# ───────────────────────── Health cards ─────────────────────────

@dataclass(frozen=True, slots=True)
class HealthCard:
    label: str
    value: str
    sub: str = ""
    status: HealthStatus = "ok"


def health_card_markdown(card: HealthCard) -> str:
    cls = {"ok": "", "warn": " is-warn", "crit": " is-crit"}[card.status]
    sub_html = f'<div class="enel-health-sub">{escape(card.sub)}</div>' if card.sub else ""
    return (
        f'<div class="enel-health-card{cls}" role="group">'
        f'<div class="enel-health-label">{escape(card.label)}</div>'
        f'<div class="enel-health-value">{escape(card.value)}</div>'
        f"{sub_html}"
        "</div>"
    )


def health_grid_markdown(cards: Sequence[HealthCard]) -> str:
    if not cards:
        return ""
    return (
        '<div class="enel-health-grid" role="list">'
        + "".join(health_card_markdown(c) for c in cards)
        + "</div>"
    )


def render_health_grid(st: Any, cards: Sequence[HealthCard]) -> None:  # pragma: no cover
    st.markdown(health_grid_markdown(cards), unsafe_allow_html=True)


# ───────────────────────── Topic pills ─────────────────────────

@dataclass(frozen=True, slots=True)
class TopicPill:
    name: str
    count: int | str = ""


def topic_pills_markdown(pills: Sequence[TopicPill]) -> str:
    if not pills:
        return ""
    items: list[str] = []
    for p in pills:
        count_html = f'<span class="n">{escape(str(p.count))}</span>' if p.count != "" else ""
        items.append(
            f'<span class="enel-topic-pill"><span>{escape(p.name)}</span>{count_html}</span>'
        )
    return f'<div class="enel-topics" role="list">{"".join(items)}</div>'


def render_topic_pills(st: Any, pills: Sequence[TopicPill]) -> None:  # pragma: no cover
    st.markdown(topic_pills_markdown(pills), unsafe_allow_html=True)


# ───────────────────────── Topbar status ─────────────────────────

def topbar_markdown(*, crumb: str, status: str = "Silver sincronizado") -> str:
    parts = crumb.split(" / ")
    if len(parts) > 1:
        crumb_html = (
            " <span style=\"color:var(--text-faint)\">/</span> ".join(
                escape(p) if i < len(parts) - 1 else f"<b>{escape(p)}</b>"
                for i, p in enumerate(parts)
            )
        )
    else:
        crumb_html = f"<b>{escape(crumb)}</b>"
    return (
        '<div class="enel-topbar" role="status" aria-live="polite">'
        f'<div class="enel-crumbs">{crumb_html}</div>'
        f'<div class="enel-status"><span class="enel-pulse" aria-hidden="true"></span>{escape(status)}</div>'
        "</div>"
    )


def render_topbar(st: Any, *, crumb: str, status: str = "Silver sincronizado") -> None:  # pragma: no cover
    st.markdown(topbar_markdown(crumb=crumb, status=status), unsafe_allow_html=True)


__all__ = [
    "HealthCard",
    "KPI",
    "ParetoItem",
    "StoryBlock",
    "TopicPill",
    "health_card_markdown",
    "health_grid_markdown",
    "insight_markdown",
    "kpi_card_markdown",
    "kpi_strip_markdown",
    "pareto_markdown",
    "render_health_grid",
    "render_insight",
    "render_kpi_strip",
    "render_pareto",
    "render_story",
    "render_topbar",
    "render_topic_pills",
    "story_block_markdown",
    "topbar_markdown",
    "topic_pills_markdown",
]
