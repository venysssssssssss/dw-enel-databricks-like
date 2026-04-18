from __future__ import annotations

from typing import Any

import pandas as pd
import plotly.express as px

from apps.streamlit.components.narrative import download_dataframe
from apps.streamlit.components.premium import (
    KPI,
    ParetoItem,
    StoryBlock,
    kpi_strip_markdown,
    pareto_markdown,
    render_story,
    render_topbar,
)
from apps.streamlit.layers.common import (
    aggregate,
    color_sequence,
    render_chart,
    render_table_or_empty,
)
from apps.streamlit.theme import SEQUENTIAL_BLUE, SEQUENTIAL_ORANGE, format_int, format_pct
from src.viz.erro_leitura_dashboard_data import (
    mis_executive_summary,
    mis_monthly_mis,
    severity_heatmap,
    taxonomy_reference,
)


def render(st: Any, frame, *, theme: str = "light") -> None:
    render_topbar(st, crumb="MIS / BI MIS Executivo", status="Silver sincronizado")
    render_story(
        st,
        StoryBlock(
            icon="◆",
            lead="Ritmo, concentração e reincidência num só golpe de vista.",
            body=(
                "Use o <b>tema dominante</b> como hipótese, depois desça para "
                "<b>Ritmo Operacional</b> para confirmar a curva e em <b>Padrões</b> "
                "para isolar causa × região."
            ),
            steps=(
                "Identifique a curva anômala",
                "Cruze com causa dominante",
                "Valide na taxonomia IA",
                "Leve ao comitê de risco",
            ),
        ),
    )

    summary = aggregate(mis_executive_summary, frame)
    monthly = aggregate(mis_monthly_mis, frame)
    severity = aggregate(severity_heatmap, frame)

    # ── KPI strip (premium) ──
    _render_kpi_strip(st, summary, frame)

    # ── DOM Pareto (macro region) + Plotly trend side-by-side ──
    left, right = st.columns([1.0, 1.0], gap="large")
    with left:
        st.markdown(
            '<div class="enel-card" style="padding:20px 22px">'
            '<div style="font-family:var(--font-display);font-weight:700;font-size:18px;'
            'letter-spacing:-0.01em;margin-bottom:4px">Concentração por região</div>'
            '<div style="font-size:12px;color:var(--text-dim);margin-bottom:14px">'
            "Ordens por região · Pareto nativo com gradiente accent</div>",
            unsafe_allow_html=True,
        )
        st.markdown(_region_pareto_html(summary), unsafe_allow_html=True)
        st.markdown(
            '<div class="enel-insight"><span class="label">Insight</span>'
            f"{_region_insight(summary)}</div></div>",
            unsafe_allow_html=True,
        )

    with right:
        if not monthly.empty:
            fig = px.line(
                monthly,
                x="mes_ingresso",
                y="qtd_erros",
                color="regiao",
                markers=True,
                line_shape="spline",
                title="Tendência mensal por região",
                color_discrete_sequence=color_sequence(),
                labels={
                    "mes_ingresso": "Mês de ingresso",
                    "qtd_erros": "Ordens",
                    "regiao": "Região",
                },
            )
            fig.update_traces(
                line={"width": 2.5},
                marker={"size": 7, "line": {"width": 1.5, "color": "rgba(255,255,255,0.85)"}},
                hovertemplate="<b>%{x|%b/%Y}</b><br>%{fullData.name}: %{y:,d} ordens<extra></extra>",
            )
            render_chart(st, fig, key="mis_monthly", theme=theme, height=360)
            download_dataframe(st, "📥 CSV tendência MIS", monthly, section="mis_tendencia")

    # ── Severidade heatmap com insight ──
    if not severity.empty:
        fig = px.density_heatmap(
            severity,
            x="severidade",
            y="regiao",
            z="qtd_erros",
            color_continuous_scale=SEQUENTIAL_ORANGE + SEQUENTIAL_BLUE,
            title="Severidade por região",
            labels={"severidade": "Severidade", "regiao": "Região", "qtd_erros": "Ordens"},
            text_auto=True,
        )
        fig.update_traces(
            hovertemplate="<b>%{y}</b> · severidade <b>%{x}</b><br>%{z:,d} ordens<extra></extra>",
            textfont={"size": 11, "color": "#F8F9FB" if theme == "dark" else "#1D1F24"},
        )
        fig.update_layout(coloraxis_colorbar={"title": "Ordens", "thickness": 12})
        render_chart(st, fig, key="mis_severity", theme=theme, height=360)
        st.markdown(
            '<div class="enel-insight"><span class="label">Insight</span>'
            f"{_severity_insight(severity)}</div>",
            unsafe_allow_html=True,
        )

    # ── Executive summary table (fallback detalhado) ──
    with st.expander("Resumo executivo detalhado por região"):
        render_table_or_empty(st, summary, section="mis_executivo")

    with st.expander("Referência de taxonomia operacional"):
        render_table_or_empty(st, taxonomy_reference(), section="taxonomia_referencia")


# ───────────────────────── helpers ─────────────────────────

def _render_kpi_strip(st: Any, summary: pd.DataFrame, frame: pd.DataFrame) -> None:
    total = int(summary["volume_total"].sum()) if not summary.empty else len(frame)
    kpis: list[KPI] = [
        KPI(
            label="Volume total",
            value=format_int(total),
            tag="ordens",
        ),
    ]
    if not summary.empty:
        top = summary.sort_values("volume_total", ascending=False).iloc[0]
        kpis.append(
            KPI(
                label="Região dominante",
                value=str(top["regiao"]),
                tag=format_int(int(top["volume_total"])),
                delta=f"{top['volume_total'] / total * 100:.1f}% do total" if total else "",
            )
        )
        kpis.append(
            KPI(
                label="Causa dominante",
                value=str(top["causa_dominante"]),
                tag="canônica",
                delta=f"{format_pct(float(top['share_causa_dominante']))} da região",
                dominant=True,
            )
        )
        refat = float((summary["taxa_refaturamento"] * summary["volume_total"]).sum() / total) if total else 0.0
        kpis.append(
            KPI(
                label="Taxa refaturamento",
                value=format_pct(refat),
                tag="ponderada",
                delta="meta ≤ 10%" if refat > 0.10 else "dentro da meta",
                delta_intent="up_bad" if refat > 0.10 else "neutral",
            )
        )
        reinc = int(summary["instalacoes_reincidentes"].sum())
        kpis.append(
            KPI(
                label="Instalações reincidentes",
                value=format_int(reinc),
                tag="≥ 2 ordens",
            )
        )
    st.markdown(kpi_strip_markdown(kpis), unsafe_allow_html=True)


def _region_pareto_html(summary: pd.DataFrame) -> str:
    if summary.empty:
        return '<div class="enel-empty">Sem dados para esta região.</div>'
    total = float(summary["volume_total"].sum())
    items = [
        ParetoItem(
            name=str(row["regiao"]),
            value=float(row["volume_total"]),
            pct=(row["volume_total"] / total * 100.0) if total else 0.0,
        )
        for _, row in summary.sort_values("volume_total", ascending=False).iterrows()
    ]
    return pareto_markdown(items, highlight_first=True)


def _region_insight(summary: pd.DataFrame) -> str:
    if summary.empty:
        return "Sem sinal suficiente para narrar."
    ordered = summary.sort_values("volume_total", ascending=False)
    top = ordered.iloc[0]
    total = float(summary["volume_total"].sum())
    share = top["volume_total"] / total * 100.0 if total else 0.0
    return (
        f"<b>{top['regiao']}</b> concentra <b>{share:.1f}%</b> do volume "
        f"com causa dominante <b>{top['causa_dominante']}</b> "
        f"({format_pct(float(top['share_causa_dominante']))} intra-região)."
    )


def _severity_insight(severity: pd.DataFrame) -> str:
    if severity.empty or "qtd_erros" not in severity.columns:
        return "Sem dados de severidade."
    by_reg = severity.groupby("regiao")["qtd_erros"].sum()
    if len(by_reg) < 2:
        total = int(by_reg.sum())
        return f"Volume agregado: <b>{format_int(total)}</b> ordens."
    top_reg = by_reg.idxmax()
    ratio = by_reg.max() / max(by_reg.min(), 1)
    return (
        f"<b>{top_reg}</b> lidera o volume severo com razão de <b>{ratio:.1f}×</b> "
        "frente à segunda região — pressão operacional concentrada."
    )
