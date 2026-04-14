"""Streamlit dashboard for Sprint 13 erro de leitura intelligence.

Dashboard estruturado em camadas progressivas:

    0. Hero + KPIs executivos
    1. Ritmo operacional (tendencia temporal + Pareto de causas)
    2. Padroes e concentracoes (heatmap regiao x causa, topicos)
    3. Impacto financeiro (refaturamento)
    4. Taxonomia descoberta (BERTopic)
    5. Governanca analitica
    6. Sessao educacional (como cada visao foi construida)

Cada camada tem titulo, descricao curta do que responde e o grafico em si.
"""

from __future__ import annotations

import sys
from pathlib import Path

try:
    import pandas as pd
    import plotly.express as px
    import streamlit as st
except ModuleNotFoundError as exc:  # pragma: no cover - runtime guidance for optional UI deps.
    missing = exc.name
    raise SystemExit(
        f"Dependencia visual ausente: {missing}. Instale com: .venv/bin/pip install -e '.[viz,ml]'"
    ) from exc


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.viz.erro_leitura_dashboard_data import (  # noqa: E402
    DEFAULT_SILVER_PATH,
    DEFAULT_TOPIC_ASSIGNMENTS_PATH,
    DEFAULT_TOPIC_TAXONOMY_PATH,
    category_breakdown,
    compute_kpis,
    load_dashboard_frame,
    mis_executive_summary,
    mis_monthly_mis,
    monthly_volume,
    radar_causes_by_region,
    refaturamento_by_cause,
    region_cause_matrix,
    reincidence_matrix,
    root_cause_distribution,
    safe_topic_taxonomy_for_display,
    severity_heatmap,
    taxonomy_reference,
    topic_distribution,
)
from src.viz.reclamacoes_ce_dashboard_data import (  # noqa: E402
    MACRO_TEMA_LABELS,
    MACRO_TEMA_ORDER,
    assunto_pareto,
    causa_raiz_drill,
    compute_kpis as compute_reclamacoes_kpis,
    cruzamento_com_erro_leitura,
    executive_summary as reclamacoes_executive_summary,
    heatmap_tema_x_mes,
    load_reclamacoes_ce,
    macro_tema_distribution,
    monthly_trend_by_tema,
    radar_tema_por_grupo,
    reincidence_matrix as reclamacoes_reincidence_matrix,
    top_instalacoes_reincidentes,
)


# Paleta ENEL — alinhada à identidade corporativa (azul + verde), com laranja/amarelo
# oficiais como cores de destaque e neutros de alto contraste. Todos os pares de texto
# sobre fundo obedecem WCAG AA (ratio ≥ 4.5:1 para corpo, ≥ 3:1 para títulos grandes).
PALETTE = {
    "primary": "#0F4C81",     # ENEL azul corporativo
    "primary_dark": "#0B3A63",
    "primary_light": "#1F6FB2",
    "secondary": "#00813E",   # ENEL verde (sustentabilidade)
    "secondary_light": "#2BA65E",
    "accent": "#F7941D",      # ENEL laranja oficial
    "accent_soft": "#FBB040",
    "warning": "#E4002B",     # Vermelho alerta ENEL
    "neutral_900": "#1A1A1A",
    "neutral_700": "#3F4A55",
    "neutral_500": "#6B7680",
    "neutral_200": "#E6ECF2",
    "neutral_50": "#F6F9FC",
    "ce": "#F7941D",          # Ceará → laranja (sol/sertão)
    "sp": "#0F4C81",          # São Paulo → azul corporativo
    "muted": "#6B7680",
}

CATEGORICAL_SEQUENCE = [
    "#0F4C81", "#F7941D", "#00813E", "#5C2D91",
    "#E4002B", "#1F6FB2", "#FBB040", "#2BA65E",
]

SEQUENTIAL_BLUE = [
    "#EAF2FA", "#C7DDF0", "#9EC4E3", "#6FA6D3",
    "#4088C0", "#1F6FB2", "#0F4C81", "#0B3A63",
]

SEQUENTIAL_ORANGE = [
    "#FFF3E0", "#FFD9A6", "#FBB040", "#F7941D",
    "#E07B10", "#B86008",
]

SEQUENTIAL_GREEN = [
    "#E6F4EC", "#B6E0C5", "#80C89C", "#2BA65E",
    "#00813E", "#005F2C",
]


def main() -> None:
    st.set_page_config(
        page_title="Erros de Leitura | Inteligencia Operacional ENEL",
        page_icon="⚡",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    _inject_style()

    st.sidebar.title("⚙ Controles")
    st.sidebar.caption("Fontes de dados e filtros analiticos")

    with st.sidebar.expander("Fontes de dados", expanded=False):
        silver_path = Path(st.text_input("Dataset Silver", str(DEFAULT_SILVER_PATH)))
        assignments_path = Path(
            st.text_input("Topic assignments", str(DEFAULT_TOPIC_ASSIGNMENTS_PATH))
        )
        taxonomy_path = Path(st.text_input("Taxonomia", str(DEFAULT_TOPIC_TAXONOMY_PATH)))

    include_total = st.sidebar.toggle(
        "Incluir reclamacao_total",
        value=False,
        help="Por padrao o dashboard considera apenas erros de leitura (CE) + Base N1 (SP). "
        "Ative para incluir todas as reclamacoes agregadas — util para investigar se erros "
        "de leitura sao causa-raiz de outros tipos de reclamacao.",
    )

    frame = _load_frame(
        silver_path=silver_path,
        assignments_path=assignments_path,
        taxonomy_path=taxonomy_path,
        include_total=include_total,
    )
    if frame.empty:
        st.warning("Nenhum registro disponivel. Verifique os caminhos de dados na barra lateral.")
        return

    filtered = _sidebar_filters(frame)
    if filtered.empty:
        st.warning(
            "Nenhum registro corresponde aos filtros selecionados. "
            "Relaxe a selecao de regiao, causa, topico ou periodo."
        )
        return

    _hero(filtered, total_available=len(frame))

    (
        tab_mis,
        tab_ce_total,
        tab_overview,
        tab_patterns,
        tab_impact,
        tab_taxonomy,
        tab_gov,
        tab_edu,
    ) = st.tabs(
        [
            "🧭 BI MIS Executivo",
            "🟧 CE · Reclamacoes Totais",
            "📈 Ritmo Operacional",
            "🗺 Padroes & Concentracoes",
            "💰 Impacto de Refaturamento",
            "🧬 Taxonomia Descoberta",
            "🛡 Governanca",
            "🎓 Sessao Educacional",
        ]
    )

    with tab_mis:
        _mis_layer(filtered)
    with tab_ce_total:
        _reclamacoes_ce_layer(silver_path=silver_path, erro_leitura_frame=frame)
    with tab_overview:
        _executive_layer(filtered)
    with tab_patterns:
        _pattern_layer(filtered)
    with tab_impact:
        _impact_layer(filtered)
    with tab_taxonomy:
        _taxonomy_layer(taxonomy_path)
    with tab_gov:
        _governance_layer(filtered)
    with tab_edu:
        _educational_layer()


@st.cache_data(show_spinner="Carregando dados analiticos...")
def _load_frame(
    *,
    silver_path: Path,
    assignments_path: Path,
    taxonomy_path: Path,
    include_total: bool,
) -> pd.DataFrame:
    return load_dashboard_frame(
        silver_path=silver_path,
        topic_assignments_path=assignments_path,
        topic_taxonomy_path=taxonomy_path,
        include_total=include_total,
    )


def _sidebar_filters(frame: pd.DataFrame) -> pd.DataFrame:
    st.sidebar.markdown("### 🎯 Filtros analiticos")

    regions = sorted(frame["regiao"].dropna().unique().tolist())
    causes = sorted(frame["causa_canonica"].dropna().unique().tolist())
    topics = sorted(frame["topic_name"].dropna().unique().tolist())

    selected_regions = st.sidebar.multiselect(
        "Regiao", regions, default=regions, help="CE = Ceara · SP = Sao Paulo"
    )
    selected_causes = st.sidebar.multiselect(
        "Causa canonica",
        causes,
        default=causes,
        help="Taxonomia canonica derivada de regra + IA. Use para isolar 1-2 classes especificas.",
    )
    selected_topics = st.sidebar.multiselect(
        "Topico descoberto",
        topics,
        default=topics,
        help="Clusters nao-supervisionados BERTopic sobre OBSERVACAO + DEVOLUTIVA.",
    )

    date_frame = frame.dropna(subset=["data_ingresso"])
    start_date = end_date = None
    if not date_frame.empty:
        min_date = date_frame["data_ingresso"].min().date()
        max_date = date_frame["data_ingresso"].max().date()
        start_date, end_date = st.sidebar.date_input(
            "Periodo",
            (min_date, max_date),
            min_value=min_date,
            max_value=max_date,
            help="Filtra por DT. INGRESSO da ordem.",
        )

    only_refaturamento = st.sidebar.toggle(
        "Somente resolvidos com refaturamento",
        value=False,
        help="Isola ordens onde a empresa aceitou retificar a conta — proxy direto de impacto financeiro.",
    )
    only_labeled = st.sidebar.toggle(
        "Somente com rotulo de origem",
        value=False,
        help="Considera apenas ordens onde Causa Raiz ja foi preenchida pelo operador (label forte).",
    )

    filtered = frame.loc[
        frame["regiao"].isin(selected_regions)
        & frame["causa_canonica"].isin(selected_causes)
        & frame["topic_name"].isin(selected_topics)
    ].copy()

    if start_date is not None and end_date is not None:
        start_ts = pd.Timestamp(start_date)
        end_ts = pd.Timestamp(end_date) + pd.Timedelta(days=1)
        filtered = filtered.loc[
            filtered["data_ingresso"].isna()
            | ((filtered["data_ingresso"] >= start_ts) & (filtered["data_ingresso"] < end_ts))
        ]

    if only_refaturamento:
        filtered = filtered.loc[filtered["flag_resolvido_com_refaturamento"]]
    if only_labeled:
        filtered = filtered.loc[filtered["has_causa_raiz_label"]]

    st.sidebar.caption(f"📊 **{len(filtered):,}** registros apos filtros".replace(",", "."))
    return filtered


def _hero(frame: pd.DataFrame, *, total_available: int) -> None:
    st.markdown(
        """
        <section class="hero">
          <div>
            <p class="eyebrow">Sprint 13 · IA de Classificacao Inteligente de Erros de Leitura</p>
            <h1>Erros de leitura como mapa operacional vivo</h1>
            <p class="subtitle">
              Visao executiva, padroes de causa-raiz, taxonomia de topicos descoberta
              por NLP e sinais de refaturamento — em um so lugar, sem expor texto livre sensivel.
            </p>
          </div>
        </section>
        """,
        unsafe_allow_html=True,
    )

    kpis = compute_kpis(frame)
    coverage = (len(frame) / total_available) if total_available else 0.0
    cards = [
        (
            "Registros filtrados",
            f"{kpis.total_registros:,}".replace(",", "."),
            f"{coverage:.0%} da base disponivel",
        ),
        (
            "Erros analisados",
            f"{kpis.total_erros:,}".replace(",", "."),
            "erro_leitura (CE) + base_n1_sp",
        ),
        (
            "Taxa de refaturamento",
            f"{kpis.taxa_refaturamento:.1%}",
            "proxy de impacto financeiro",
        ),
        (
            "Rotulo de origem",
            f"{kpis.taxa_rotulo_origem:.1%}",
            "cobertura de Causa Raiz preenchida",
        ),
        (
            "Topicos ativos",
            str(kpis.topicos),
            "clusters descobertos (BERTopic)",
        ),
        (
            "Instalacoes reincidentes",
            f"{kpis.instalacoes_reincidentes:,}".replace(",", "."),
            "IDs anonimizados (hash SHA-256)",
        ),
    ]
    cols = st.columns(len(cards))
    for column, (label, value, note) in zip(cols, cards, strict=True):
        column.markdown(
            f"""
            <div class="metric-card">
              <span>{label}</span>
              <strong>{value}</strong>
              <small>{note}</small>
            </div>
            """,
            unsafe_allow_html=True,
        )


def _mis_layer(frame: pd.DataFrame) -> None:
    """BI MIS (Management Information System) — visao 360 para tomada de decisao.

    Combina:
      - Summary executivo por regiao (volume, severidade, causa dominante, reincidencia)
      - Radar / teia de aranha: perfil de causa por regiao (top-10 causas)
      - Breakdown por categoria da taxonomia (processo, cadastro, equipamento...)
      - Matriz regiao x severidade (volume + taxa de refaturamento)
      - Serie temporal com MoM e media movel 3M
      - Perfil de reincidencia (1, 2, 3-4, 5-9, 10+ ordens por instalacao)
      - Tabela de referencia da taxonomia v2
    """
    st.markdown("### 🧭 MIS Executivo — Erros de Leitura")
    st.caption(
        "Visao gerencial 360 para decisao. "
        "Cada painel responde uma pergunta critica: *onde, quanto, quao grave, reincidente?*"
    )

    # --- Linha 1: Summary por regiao ---
    summary = mis_executive_summary(frame)
    if summary.empty:
        st.info("Sem dados para resumo executivo.")
        return

    st.markdown("#### 📋 Resumo executivo por regiao")
    st.caption("Snapshot gerencial: causa dominante, severidade media e reincidencia.")
    display_summary = summary.copy()
    display_summary["taxa_refaturamento"] = display_summary["taxa_refaturamento"].map(
        lambda value: f"{value:.1%}"
    )
    display_summary["cobertura_rotulo"] = display_summary["cobertura_rotulo"].map(
        lambda value: f"{value:.1%}"
    )
    display_summary["share_causa_dominante"] = display_summary["share_causa_dominante"].map(
        lambda value: f"{value:.1%}"
    )
    display_summary["share_critico"] = display_summary["share_critico"].map(
        lambda value: f"{value:.1%}"
    )
    st.dataframe(
        display_summary,
        use_container_width=True,
        hide_index=True,
        column_config={
            "regiao": st.column_config.TextColumn("Regiao"),
            "volume_total": st.column_config.NumberColumn("Volume", format="%d"),
            "taxa_refaturamento": st.column_config.TextColumn("Tx. Refat."),
            "cobertura_rotulo": st.column_config.TextColumn("Rotulo origem"),
            "instalacoes_reincidentes": st.column_config.NumberColumn(
                "Reincidentes", format="%d"
            ),
            "causa_dominante": st.column_config.TextColumn("Causa dominante"),
            "share_causa_dominante": st.column_config.TextColumn("% dominante"),
            "severidade_media": st.column_config.NumberColumn("Severidade (0-4)", format="%.2f"),
            "share_critico": st.column_config.TextColumn("% critico"),
        },
    )

    # --- Linha 2: Radar + Categoria ---
    left, right = st.columns([1.1, 1.0])

    radar = radar_causes_by_region(frame, top_n=10)
    with left:
        st.markdown("#### 🕸 Teia de aranha: perfil de causa por regiao")
        st.caption(
            "Compara o **perfil** de erros CE vs SP em uma unica figura. "
            "Eixos = causas canonicas; raio = share percentual sobre o total da regiao. "
            "Areas divergentes revelam problemas sistemicos especificos de cada mercado."
        )
        if radar.empty:
            st.info("Sem causas suficientes para o radar.")
        else:
            radar_display = radar.copy()
            radar_display["percentual_pct"] = radar_display["percentual"] * 100
            fig = px.line_polar(
                radar_display,
                r="percentual_pct",
                theta="causa_canonica",
                color="regiao",
                line_close=True,
                color_discrete_map={"CE": PALETTE["ce"], "SP": PALETTE["sp"]},
                hover_data={"qtd_erros": True, "percentual_pct": ":.1f"},
            )
            fig.update_traces(fill="toself", opacity=0.55)
            fig.update_layout(
                height=520,
                margin=dict(l=40, r=40, t=40, b=20),
                polar=dict(
                    radialaxis=dict(
                        ticksuffix="%",
                        gridcolor="rgba(67, 56, 36, .15)",
                        angle=90,
                    ),
                    angularaxis=dict(
                        tickfont=dict(size=11),
                        rotation=90,
                        direction="clockwise",
                    ),
                    bgcolor="rgba(255,250,241,.45)",
                ),
                legend=dict(orientation="h", yanchor="bottom", y=-0.08, xanchor="center", x=0.5),
            )
            st.plotly_chart(fig, use_container_width=True)

    category_df = category_breakdown(frame)
    with right:
        st.markdown("#### 🧱 Composicao por categoria funcional")
        st.caption(
            "Onde a perda acontece no processo? "
            "`processo_leitura`, `faturamento_por_media`, `acesso_fisico`, `equipamento`, "
            "`contestacao_cliente`, `cadastro`, `geracao_distribuida`, `regulatorio` — "
            "cada categoria aponta para um **owner** operacional diferente."
        )
        if category_df.empty:
            st.info("Sem categorias para exibir.")
        else:
            fig = px.bar(
                category_df,
                x="regiao",
                y="percentual",
                color="categoria",
                text=category_df["qtd_erros"].map(lambda value: f"{value:,}".replace(",", ".")),
                barmode="stack",
                labels={
                    "regiao": "Regiao",
                    "percentual": "% do total da regiao",
                    "categoria": "Categoria",
                },
                color_discrete_sequence=SEQUENTIAL_BLUE[::-1] + SEQUENTIAL_GREEN,
            )
            fig.update_layout(
                height=520,
                margin=dict(l=10, r=10, t=30, b=10),
                yaxis_tickformat=".0%",
                legend=dict(orientation="v", yanchor="top", y=1.0, xanchor="left", x=1.02),
            )
            st.plotly_chart(fig, use_container_width=True)

    # --- Linha 3: Severidade + Reincidencia ---
    left2, right2 = st.columns(2)

    severity = severity_heatmap(frame)
    with left2:
        st.markdown("#### 🔥 Matriz regiao × severidade")
        st.caption(
            "Severidade e atribuida pela taxonomia v2 — `critical` inclui faturamento por media, "
            "GD e ART 113. Celulas com **alta severidade + alto refaturamento** sao priorizaveis."
        )
        if severity.empty:
            st.info("Sem dados de severidade.")
        else:
            fig = px.density_heatmap(
                severity,
                x="regiao",
                y="severidade",
                z="qtd_erros",
                histfunc="sum",
                text_auto=True,
                color_continuous_scale="OrRd",
                labels={"qtd_erros": "Ordens", "severidade": "Severidade"},
            )
            fig.update_layout(height=340, margin=dict(l=10, r=10, t=30, b=10))
            st.plotly_chart(fig, use_container_width=True)

            st.caption("Taxa de refaturamento por severidade:")
            refat_table = severity.copy()
            refat_table["taxa_refaturamento"] = refat_table["taxa_refaturamento"].map(
                lambda value: f"{value:.1%}"
            )
            st.dataframe(
                refat_table, hide_index=True, use_container_width=True
            )

    reincidence = reincidence_matrix(frame)
    with right2:
        st.markdown("#### 🔁 Perfil de reincidencia por instalacao")
        st.caption(
            "Quantas instalacoes tem 1, 2, 3-4, 5-9 ou 10+ ordens no recorte. "
            "Instalacoes em faixas altas sao **candidatas a inspecao fisica** (medidor, rota, leiturista)."
        )
        if reincidence.empty:
            st.info("Sem instalacoes com hash valido para reincidencia.")
        else:
            fig = px.bar(
                reincidence,
                x="faixa",
                y="qtd_instalacoes",
                color="regiao",
                barmode="group",
                text="qtd_instalacoes",
                color_discrete_map={"CE": PALETTE["ce"], "SP": PALETTE["sp"]},
                labels={
                    "faixa": "Faixa de ordens por instalacao",
                    "qtd_instalacoes": "Instalacoes unicas",
                    "regiao": "Regiao",
                },
            )
            fig.update_traces(textposition="outside")
            fig.update_layout(height=340, margin=dict(l=10, r=10, t=30, b=10))
            st.plotly_chart(fig, use_container_width=True)

    # --- Linha 4: Serie MIS com MoM e MM3M ---
    st.markdown("#### 📈 Serie mensal com MoM e media movel 3M")
    st.caption(
        "Serie temporal por regiao com variacao mes-a-mes (MoM) e media movel de 3 meses. "
        "MoM negativo consecutivo sinaliza melhora estrutural; picos vs MM3M sinalizam eventos anomalos."
    )
    mis_monthly = mis_monthly_mis(frame)
    if mis_monthly.empty:
        st.info("Sem volume mensal suficiente.")
    else:
        fig = px.line(
            mis_monthly,
            x="mes_ingresso",
            y="qtd_erros",
            color="regiao",
            markers=True,
            color_discrete_map={"CE": PALETTE["ce"], "SP": PALETTE["sp"]},
            labels={
                "mes_ingresso": "Mes de ingresso",
                "qtd_erros": "Ordens unicas",
                "regiao": "Regiao",
            },
        )
        for regiao in mis_monthly["regiao"].unique():
            subset = mis_monthly.loc[mis_monthly["regiao"] == regiao]
            fig.add_scatter(
                x=subset["mes_ingresso"],
                y=subset["media_movel_3m"],
                mode="lines",
                name=f"{regiao} · MM3M",
                line=dict(dash="dot", width=2),
                showlegend=True,
            )
        fig.update_layout(
            height=380,
            margin=dict(l=10, r=10, t=30, b=10),
            hovermode="x unified",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        )
        st.plotly_chart(fig, use_container_width=True)

    # --- Linha 5: Taxonomia de referencia ---
    with st.expander("📘 Taxonomia v2 de causa-raiz (referencia)", expanded=False):
        st.caption(
            "Taxonomia ampliada (CE + SP) com 14 classes, 8 categorias funcionais "
            "e 4 niveis de severidade. Substitui o bucket generico `OUTROS` que dominava SP."
        )
        st.dataframe(taxonomy_reference(), hide_index=True, use_container_width=True)


@st.cache_data(show_spinner="Carregando reclamacoes CE...")
def _load_reclamacoes_ce(silver_path: Path) -> pd.DataFrame:
    return load_reclamacoes_ce(silver_path=silver_path)


def _reclamacoes_ce_layer(*, silver_path: Path, erro_leitura_frame: pd.DataFrame) -> None:
    st.markdown("### 🟧 CE · Reclamacoes Totais — Visao Analitica Ampliada")
    st.caption(
        "Base **reclamacao_total** do Ceara (~167k ordens, 15 meses). "
        "Taxonomia de negocio em 8 macro-temas derivada do campo `assunto` (label forte da ENEL) "
        "com drill-down em `causa_raiz` quando preenchida."
    )

    frame = _load_reclamacoes_ce(silver_path)
    if frame.empty:
        st.warning(
            "Nenhuma reclamacao total CE encontrada no Silver. "
            "Verifique o caminho do dataset e se o ingestor foi executado."
        )
        return

    kpis = compute_reclamacoes_kpis(frame)

    # --- KPI cards ---
    kpi_cols = st.columns(5)
    kpi_cols[0].metric("Volume total", f"{kpis.total_reclamacoes:,}".replace(",", "."))
    kpi_cols[1].metric("Instalacoes unicas", f"{kpis.unique_instalacoes:,}".replace(",", "."))
    kpi_cols[2].metric(
        "Reincidentes (>=2)",
        f"{kpis.instalacoes_reincidentes:,}".replace(",", "."),
        f"{kpis.instalacoes_reincidentes / max(kpis.unique_instalacoes, 1) * 100:.1f}%",
    )
    kpi_cols[3].metric("% Grupo B", f"{kpis.share_grupo_b * 100:.1f}%")
    kpi_cols[4].metric("Cobertura causa-raiz", f"{kpis.taxa_rotulo_causa_raiz * 100:.1f}%")

    st.divider()

    # --- Section 1: Executive summary + macro-tema distribution ---
    col_left, col_right = st.columns([1, 1.3])
    with col_left:
        st.markdown("**Resumo executivo**")
        st.caption("Indicadores consolidados do periodo completo.")
        st.dataframe(
            reclamacoes_executive_summary(frame),
            hide_index=True,
            use_container_width=True,
        )
    with col_right:
        st.markdown("**Distribuicao por macro-tema**")
        st.caption("55% das reclamacoes concentram-se em refaturamento/cobranca. Use para priorizar tratativa.")
        dist = macro_tema_distribution(frame)
        fig = px.bar(
            dist,
            x="qtd",
            y="macro_tema_label",
            orientation="h",
            text=dist["percentual"].map(lambda v: f"{v:.1f}%"),
            color="macro_tema_label",
            color_discrete_sequence=SEQUENTIAL_BLUE[::-1],
        )
        fig.update_layout(
            showlegend=False,
            height=360,
            margin=dict(l=10, r=10, t=10, b=10),
            yaxis={"categoryorder": "total ascending"},
            xaxis_title="Quantidade",
            yaxis_title="",
        )
        fig.update_traces(textposition="outside")
        st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # --- Section 2: Pareto 80/20 ---
    st.markdown("**Pareto 80/20 dos assuntos**")
    st.caption("Os assuntos dominantes concentram a maior parte do volume. Atacando o topo, resolve-se 80% do problema.")
    pareto = assunto_pareto(frame, top_n=20)
    fig_pareto = px.bar(
        pareto,
        x="assunto",
        y="qtd",
        text=pareto["percentual"].map(lambda v: f"{v:.1f}%"),
        color="qtd",
        color_continuous_scale=SEQUENTIAL_BLUE,
    )
    fig_pareto.add_scatter(
        x=pareto["assunto"],
        y=pareto["acumulado_pct"] / 100 * pareto["qtd"].max(),
        mode="lines+markers",
        name="Acumulado (%)",
        yaxis="y2",
        line=dict(color=PALETTE["primary"], width=2),
    )
    fig_pareto.update_layout(
        height=440,
        margin=dict(l=10, r=10, t=10, b=140),
        xaxis_tickangle=-45,
        yaxis=dict(title="Quantidade"),
        yaxis2=dict(title="Acumulado (%)", overlaying="y", side="right", range=[0, 100]),
        coloraxis_showscale=False,
        showlegend=False,
    )
    st.plotly_chart(fig_pareto, use_container_width=True)

    st.divider()

    # --- Section 3: Monthly trend + heatmap ---
    col_trend, col_heatmap = st.columns([1.2, 1])
    with col_trend:
        st.markdown("**Evolucao mensal por macro-tema (MM3M)**")
        st.caption("Volume mensal com media movel de 3 meses. Util para detectar picos sistemicos.")
        trend = monthly_trend_by_tema(frame)
        fig_trend = px.line(
            trend,
            x="ano_mes",
            y="media_movel_3m",
            color="macro_tema_label",
            markers=True,
            color_discrete_sequence=CATEGORICAL_SEQUENCE,
        )
        fig_trend.update_layout(
            height=400,
            margin=dict(l=10, r=10, t=10, b=10),
            xaxis_title="Mes",
            yaxis_title="Volume (MM3M)",
            legend=dict(orientation="h", y=-0.25),
        )
        st.plotly_chart(fig_trend, use_container_width=True)
    with col_heatmap:
        st.markdown("**Heatmap tema x mes**")
        st.caption("Intensidade por celula revela sazonalidade e picos.")
        heatmap = heatmap_tema_x_mes(frame)
        fig_heat = px.imshow(
            heatmap,
            color_continuous_scale=SEQUENTIAL_BLUE,
            aspect="auto",
            labels=dict(x="Mes", y="Macro-tema", color="Volume"),
        )
        fig_heat.update_layout(
            height=400,
            margin=dict(l=10, r=10, t=10, b=10),
            xaxis_tickangle=-45,
        )
        st.plotly_chart(fig_heat, use_container_width=True)

    st.divider()

    # --- Section 4: Radar GA vs GB + causa-raiz drill ---
    col_radar, col_drill = st.columns([1, 1.1])
    with col_radar:
        st.markdown("**Perfil de reclamacao: Grupo A vs Grupo B**")
        st.caption("Como o mix de causas difere entre GA (corporativo) e GB (residencial/comercial).")
        radar = radar_tema_por_grupo(frame)
        radar = radar.loc[radar["grupo"].isin(["GA", "GB"])]
        fig_radar = px.line_polar(
            radar,
            r="percentual",
            theta="macro_tema_label",
            color="grupo",
            line_close=True,
            color_discrete_map={"GA": PALETTE["primary"], "GB": PALETTE["accent"]},  # azul vs laranja ENEL
        )
        fig_radar.update_traces(fill="toself", opacity=0.55)
        fig_radar.update_layout(
            height=430,
            margin=dict(l=40, r=40, t=20, b=20),
            polar=dict(radialaxis=dict(ticksuffix="%", range=[0, max(radar["percentual"].max() * 1.1, 5)])),
            legend=dict(orientation="h", y=-0.1),
        )
        st.plotly_chart(fig_radar, use_container_width=True)
    with col_drill:
        st.markdown("**Drill-down em causa-raiz**")
        st.caption("Quando o operador preencheu `Causa Raiz`, qual a distribuicao por macro-tema?")
        tema_escolhido_label = st.selectbox(
            "Macro-tema para drill",
            options=[MACRO_TEMA_LABELS[t] for t in MACRO_TEMA_ORDER],
            index=0,
        )
        tema_key = next(t for t, lbl in MACRO_TEMA_LABELS.items() if lbl == tema_escolhido_label)
        drill = causa_raiz_drill(frame, macro_tema=tema_key, top_n=12)
        if drill.empty:
            st.info("Este macro-tema ainda nao possui causas-raiz preenchidas.")
        else:
            fig_drill = px.bar(
                drill,
                x="qtd",
                y="causa_raiz",
                orientation="h",
                text=drill["percentual"].map(lambda v: f"{v:.1f}%"),
                color="qtd",
                color_continuous_scale=SEQUENTIAL_BLUE,
            )
            fig_drill.update_layout(
                height=430,
                margin=dict(l=10, r=10, t=10, b=10),
                yaxis={"categoryorder": "total ascending"},
                xaxis_title="Quantidade",
                yaxis_title="",
                coloraxis_showscale=False,
            )
            fig_drill.update_traces(textposition="outside")
            st.plotly_chart(fig_drill, use_container_width=True)

    st.divider()

    # --- Section 5: Reincidence + top installations + crossover with erro_leitura ---
    col_re1, col_re2, col_cross = st.columns([1, 1, 1.2])
    with col_re1:
        st.markdown("**Reincidencia por instalacao**")
        st.caption("Quantas instalacoes reclamam N vezes no periodo.")
        reinc = reclamacoes_reincidence_matrix(frame)
        fig_reinc = px.bar(
            reinc,
            x="bucket",
            y="instalacoes",
            text="instalacoes",
            color="bucket",
            color_discrete_sequence=SEQUENTIAL_BLUE,
        )
        fig_reinc.update_layout(
            height=360,
            margin=dict(l=10, r=10, t=10, b=10),
            showlegend=False,
            xaxis_title="Reclamacoes por instalacao",
            yaxis_title="Instalacoes",
        )
        fig_reinc.update_traces(textposition="outside")
        st.plotly_chart(fig_reinc, use_container_width=True)
    with col_re2:
        st.markdown("**Top instalacoes reincidentes**")
        st.caption("Clientes que mais geram ordens — candidatos a tratativa individualizada.")
        top_inst = top_instalacoes_reincidentes(frame, top_n=15).copy()
        top_inst["ultimo_ingresso"] = pd.to_datetime(top_inst["ultimo_ingresso"]).dt.strftime("%Y-%m-%d")
        st.dataframe(
            top_inst.rename(
                columns={
                    "instalacao_hash": "Instalacao (hash)",
                    "qtd_reclamacoes": "Qtd",
                    "temas_distintos": "Temas distintos",
                    "ultimo_ingresso": "Ultimo ingresso",
                }
            ),
            hide_index=True,
            use_container_width=True,
            height=360,
        )
    with col_cross:
        st.markdown("**Cruzamento com erros de leitura (CE)**")
        st.caption(
            "Para cada macro-tema, quantas reclamacoes vieram de instalacoes que TAMBEM tem erro de leitura. "
            "Indicador direto: erro de leitura e causa-raiz oculta de outras reclamacoes?"
        )
        cross = cruzamento_com_erro_leitura(frame, erro_leitura_frame)
        if cross.empty:
            st.info("Sem interseccao detectada (verifique se os dois datasets estao carregados).")
        else:
            fig_cross = px.bar(
                cross,
                x="percentual",
                y="macro_tema_label",
                orientation="h",
                text=cross["percentual"].map(lambda v: f"{v:.1f}%"),
                color="percentual",
                color_continuous_scale=SEQUENTIAL_BLUE,
            )
            fig_cross.update_layout(
                height=360,
                margin=dict(l=10, r=10, t=10, b=10),
                yaxis={"categoryorder": "total ascending"},
                xaxis_title="% com erro de leitura",
                yaxis_title="",
                coloraxis_showscale=False,
            )
            fig_cross.update_traces(textposition="outside")
            st.plotly_chart(fig_cross, use_container_width=True)

    # --- Section 6: Taxonomy reference ---
    with st.expander("📖 Taxonomia de macro-temas (regras)"):
        taxonomy_ref = pd.DataFrame(
            [
                {
                    "macro_tema": key,
                    "label": MACRO_TEMA_LABELS[key],
                    "volume": int((frame["macro_tema"] == key).sum()),
                    "share_%": round(float((frame["macro_tema"] == key).mean() * 100), 2),
                }
                for key in MACRO_TEMA_ORDER
            ]
        )
        st.dataframe(taxonomy_ref, hide_index=True, use_container_width=True)
        st.markdown(
            "**Critério**: `assunto` (normalizado upper) é testado contra listas de tokens, "
            "ordenadas por precedência (ouvidoria/jurídico → GD → religação/multas → "
            "entrega de fatura → média/estimativa → variação de consumo → refaturamento → outros). "
            "Primeiro match vence. Quando `causa_raiz` existe, é usada para drill-down, não para reclassificação."
        )


def _executive_layer(frame: pd.DataFrame) -> None:
    st.markdown("### 1 · Ritmo Operacional")
    st.caption(
        "Como o volume de erros se comporta no tempo e quais causas dominam a base. "
        "Responde: *com que frequencia?* e *quais padroes predominam?*"
    )

    left, right = st.columns([1.35, 1.0])

    trend = monthly_volume(frame)
    with left:
        st.markdown("**Evolucao mensal por regiao**")
        st.caption(
            "Linha mensal (count distinto de ORDEM) por regiao. "
            "Picos indicam campanhas, eventos climaticos ou falhas sistemicas."
        )
        if trend.empty:
            st.info("Sem datas suficientes para serie temporal.")
        else:
            fig = px.area(
                trend,
                x="mes_ingresso",
                y="qtd_erros",
                color="regiao",
                markers=True,
                color_discrete_map={"CE": PALETTE["ce"], "SP": PALETTE["sp"]},
                labels={
                    "mes_ingresso": "Mes de ingresso",
                    "qtd_erros": "Ordens unicas",
                    "regiao": "Regiao",
                },
            )
            fig.update_layout(
                height=420,
                margin=dict(l=10, r=10, t=30, b=10),
                hovermode="x unified",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            )
            st.plotly_chart(fig, use_container_width=True)

    with right:
        st.markdown("**Pareto de causas canonicas**")
        st.caption(
            "Ranking de causas ordenadas por volume. "
            "A cor indica a taxa de refaturamento — quanto mais escura, maior o impacto financeiro."
        )
        causes = root_cause_distribution(frame)
        if causes.empty:
            st.info("Sem causas para exibir.")
        else:
            fig = px.bar(
                causes,
                x="qtd_erros",
                y="causa_canonica",
                orientation="h",
                color="taxa_refaturamento",
                text="qtd_erros",
                hover_data={"percentual": ":.1%", "taxa_refaturamento": ":.1%"},
                color_continuous_scale="Brwnyl",
                labels={
                    "qtd_erros": "Ordens unicas",
                    "causa_canonica": "Causa canonica",
                    "taxa_refaturamento": "Tx. refat.",
                },
            )
            fig.update_traces(textposition="outside")
            fig.update_layout(
                height=420,
                margin=dict(l=10, r=10, t=30, b=10),
                yaxis={"categoryorder": "total ascending"},
            )
            st.plotly_chart(fig, use_container_width=True)


def _pattern_layer(frame: pd.DataFrame) -> None:
    st.markdown("### 2 · Padroes e Concentracoes")
    st.caption(
        "Onde os erros se concentram geograficamente e quais agrupamentos semanticos emergem. "
        "Responde: *por que acontecem?* e *de que maneira?*"
    )

    left, right = st.columns(2)

    with left:
        st.markdown("**Mapa de calor: regiao x causa**")
        st.caption(
            "Heatmap cruzando regiao e causa canonica. "
            "Celulas escuras sinalizam pares regiao+causa com concentracao atipica."
        )
        matrix = region_cause_matrix(frame)
        if matrix.empty or matrix.shape[1] <= 1:
            st.info("Sem dados suficientes para matriz.")
        else:
            melted = matrix.melt(
                id_vars="causa_canonica", var_name="regiao", value_name="qtd_erros"
            )
            fig = px.density_heatmap(
                melted,
                x="regiao",
                y="causa_canonica",
                z="qtd_erros",
                histfunc="sum",
                color_continuous_scale="YlOrBr",
                text_auto=True,
                labels={
                    "regiao": "Regiao",
                    "causa_canonica": "Causa",
                    "qtd_erros": "Ordens",
                },
            )
            fig.update_layout(height=460, margin=dict(l=10, r=10, t=30, b=10))
            st.plotly_chart(fig, use_container_width=True)

    with right:
        st.markdown("**Mapa de topicos descobertos (BERTopic)**")
        st.caption(
            "Cada retangulo e um topico descoberto por NLP nao-supervisionado sobre os campos livres. "
            "Tamanho = volume, cor = taxa de refaturamento. Passe o mouse para ver palavras-chave."
        )
        topics = topic_distribution(frame)
        if topics.empty or topics["qtd_erros"].sum() == 0:
            st.info("Sem topicos ainda. Rode `make erro-leitura-train`.")
        else:
            fig = px.treemap(
                topics,
                path=["topic_name"],
                values="qtd_erros",
                color="taxa_refaturamento",
                hover_data={"topic_keywords": True, "taxa_refaturamento": ":.1%"},
                color_continuous_scale="Tealgrn",
            )
            fig.update_layout(height=460, margin=dict(l=10, r=10, t=30, b=10))
            st.plotly_chart(fig, use_container_width=True)


def _impact_layer(frame: pd.DataFrame) -> None:
    st.markdown("### 3 · Impacto de Refaturamento")
    st.caption(
        "Quais causas mais geram retificacao financeira para o cliente — onde agir tem ROI direto."
    )

    refat = refaturamento_by_cause(frame)
    if refat.empty:
        st.info("Sem dados de refaturamento no recorte atual.")
        return

    fig = px.bar(
        refat,
        x="causa_canonica",
        y="taxa_refaturamento",
        color="qtd_erros",
        text="qtd_erros",
        hover_data={"qtd_erros": True, "taxa_refaturamento": ":.1%"},
        color_continuous_scale="Cividis",
        labels={
            "causa_canonica": "Causa canonica",
            "taxa_refaturamento": "Taxa de refaturamento",
            "qtd_erros": "Ordens",
        },
    )
    fig.update_traces(texttemplate="%{text} ord.", textposition="outside")
    fig.update_layout(
        height=430,
        margin=dict(l=10, r=10, t=30, b=10),
        yaxis_tickformat=".0%",
        uniformtext_minsize=10,
    )
    st.plotly_chart(fig, use_container_width=True)

    with st.expander("Como ler este grafico"):
        st.markdown(
            """
- **Altura da barra** = `% de ordens resolvidas com refaturamento` para aquela causa.
- **Cor** = volume absoluto (quanto mais clara, mais ordens).
- Causa com **alta barra + cor clara** = prioridade maxima (muito volume *e* muito impacto).
- Causa com **alta barra + cor escura** = poucas ocorrencias, mas quase todas geram retificacao.
            """
        )


def _taxonomy_layer(taxonomy_path: Path) -> None:
    st.markdown("### 4 · Taxonomia Descoberta")
    st.caption(
        "Clusters nao-supervisionados produzidos por BERTopic sobre os textos livres. "
        "Cada topico tem um ID, um nome humano, volume e palavras-chave representativas."
    )
    if not taxonomy_path.exists():
        st.info(
            "Taxonomia ainda nao encontrada. Gere com: `make erro-leitura-train`. "
            f"Arquivo esperado: `{taxonomy_path}`"
        )
        return
    taxonomy = pd.read_json(taxonomy_path)
    safe_taxonomy = safe_topic_taxonomy_for_display(taxonomy)
    table = safe_taxonomy[["topic_id", "topic_name", "topic_size", "topic_keywords"]].sort_values(
        "topic_size",
        ascending=False,
    )
    st.dataframe(
        table,
        use_container_width=True,
        hide_index=True,
        column_config={
            "topic_id": st.column_config.TextColumn("ID", width="small"),
            "topic_name": st.column_config.TextColumn("Nome do topico"),
            "topic_size": st.column_config.NumberColumn("Volume", format="%d"),
            "topic_keywords": st.column_config.TextColumn("Palavras-chave"),
        },
    )

    with st.expander("🔍 Amostras mascaradas por topico (PII-safe)"):
        st.caption(
            "Exemplos representativos com mascaramento automatico de telefone, CEP, e-mail e protocolo."
        )
        for row in safe_taxonomy.sort_values("topic_size", ascending=False).itertuples(index=False):
            st.markdown(f"**{row.topic_name}** · {row.topic_size} registros")
            for example in getattr(row, "examples", []) or []:
                st.caption(f"› {example}")


def _governance_layer(frame: pd.DataFrame) -> None:
    st.markdown("### 5 · Governanca Analitica")
    st.caption("Princípios de privacidade e fontes autoritativas desta plataforma.")

    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown(
            """
#### 🔒 Privacidade de dados
- Nao exibimos `observacao_ordem`, `devolutiva`, telefones, e-mails, CEPs ou protocolos brutos.
- `instalacao` aparece **apenas como hash SHA-256 truncado** para medir reincidencia agregada.
- Amostras textuais passam por mascaramento automatico antes de virar visualizacao.
            """
        )
    with col_b:
        st.markdown(
            """
#### 📚 Fontes autoritativas
- **Silver**: `data/silver/erro_leitura_normalizado.csv` (schema unificado CE+SP).
- **Topicos**: `data/model_registry/erro_leitura/` (BERTopic — retreino semanal).
- **Causa canonica**: label de origem (CE) com fallback de classificador keyword-based.
- **Superset/Gold**: consumira a camada Gold quando Trino/dbt estiverem validados em prod.
            """
        )

    st.markdown("#### 📊 Distribuicao do recorte atual")
    dist = (
        frame.groupby(["regiao", "tipo_origem"], as_index=False)
        .agg(qtd_ordens=("ordem", "nunique"))
        .sort_values("qtd_ordens", ascending=False)
    )
    st.dataframe(dist, use_container_width=True, hide_index=True)


def _educational_layer() -> None:
    st.markdown("### 6 · Sessao Educacional")
    st.caption(
        "Como cada visao deste dashboard foi construida — do dado bruto ao grafico. "
        "Use esta sessao para onboarding de analistas e coordenacao."
    )

    st.markdown(
        """
#### 🏗 Arquitetura do pipeline de dados

```
Excel (DESCRICOES_ENEL/)
  → BRONZE   (Iceberg: raw + _run_id, _ingested_at, _source_region, _sheet_name)
  → SILVER   (normalizado CE+SP, dedup por ORDEM, texto limpo, entidades extraidas)
  → GOLD     (fato_erro_leitura + dim_causa_raiz + dim_regiao + dim_tempo)
  → ML       (BERTopic para topicos · classificador keyword/LightGBM para causa canonica)
  → STREAMLIT (este dashboard consome Silver + artefatos ML diretamente)
```
        """
    )

    st.markdown("---")

    with st.expander("📈 Visao 1 — Evolucao mensal por regiao (Ritmo Operacional)", expanded=False):
        st.markdown(
            """
**Pergunta respondida:** *com que frequencia os erros ocorrem ao longo do tempo, separados por regiao?*

**Pipeline:**
1. Silver carrega `dt_ingresso` como string → convertido com `pd.to_datetime(..., errors="coerce")`.
2. Derivamos `mes_ingresso = data_ingresso.dt.to_period("M").dt.to_timestamp()` (ancora no 1º dia do mes).
3. `monthly_volume(frame)` agrupa por `(mes_ingresso, regiao)` e aplica `nunique(ordem)` para evitar dupla contagem.
4. Render em `plotly.express.area` com `color=regiao` — paleta fixa CE=laranja, SP=verde-escuro.

**Decisoes de design:**
- `nunique` ao inves de `count` → robusto a duplicatas residuais no Silver.
- Area ao inves de linha → sinaliza volume absoluto; laranja (CE) + verde (SP) em paleta ENEL.
- `hovermode="x unified"` → comparacao CE vs SP no mesmo mes em um unico tooltip.
            """
        )

    with st.expander("📊 Visao 2 — Pareto de causas canonicas"):
        st.markdown(
            """
**Pergunta respondida:** *quais causas concentram o maior volume e quais tem o maior impacto financeiro?*

**Pipeline:**
1. `causa_canonica` vem de `canonical_label()` sobre `causa_raiz` (label de operador, parcial).
2. Se ausente, fallback: `KeywordErroLeituraClassifier().classify(texto_completo)` — regra determinista baseada em dicionario de termos.
3. `root_cause_distribution(frame, limit=12)` faz `groupby(causa_canonica).agg(nunique(ordem), mean(flag_refat))`.
4. `plotly.express.bar` horizontal + `color_continuous_scale="Brwnyl"` (marrom → laranja).

**Por que essa escolha?**
- Ordenacao `total ascending` no eixo Y garante topo-visual no topo do grafico (UX de Pareto classico).
- Cor codifica uma **segunda metrica** (taxa de refaturamento) sem precisar de segundo grafico.
- Limite de 12 causas → cabe na tela sem scroll, representando >90% do volume tipicamente.
            """
        )

    with st.expander("🗺 Visao 3 — Mapa de calor regiao x causa"):
        st.markdown(
            """
**Pergunta respondida:** *existem pares (regiao, causa) com concentracao atipica?*

**Pipeline:**
1. `region_cause_matrix(frame)` faz `pivot_table(index=causa, columns=regiao, values=ordem, aggfunc="nunique", fill_value=0)`.
2. `.melt()` reverte para formato longo — exigencia do `density_heatmap`.
3. `plotly.express.density_heatmap` com `histfunc="sum"` e `text_auto=True` para rotulos nas celulas.

**Por que esse grafico?**
- Heatmap e visualmente denso — perfeito para identificar **outliers geograficos** (ex: "leitura estimada" desproporcional em SP).
- Escala YlOrBr (amarelo → laranja → marrom) funciona em daltonismo comum e combina com tema ENEL.
            """
        )

    with st.expander("🧬 Visao 4 — Treemap de topicos (BERTopic)"):
        st.markdown(
            """
**Pergunta respondida:** *quais agrupamentos semanticos emergem dos textos livres, sem intervencao humana?*

**Pipeline de ML:**
1. **Embeddings** via `sentence-transformers` (`paraphrase-multilingual-MiniLM-L12-v2`, 384-d, PT-BR).
   - Input: `observacao_ordem + devolutiva` concatenados.
2. **UMAP** reduz 384-d → 5-d preservando estrutura local (`n_neighbors=15`).
3. **HDBSCAN** clusteriza os embeddings reduzidos (`min_cluster_size=20`) — clusters com densidade variavel, sem precisar definir `k`.
4. **c-TF-IDF** extrai palavras-chave por cluster; primeiros 2-3 termos viram nome do topico.

**Pipeline visual:**
1. `topic_distribution(frame)` agrupa por `(topic_name, topic_keywords)` com `nunique(ordem)` + `mean(flag_refat)`.
2. `plotly.express.treemap` — tamanho = volume, cor = taxa de refaturamento.

**Por que treemap?**
- Ocupa todo o retangulo → nao desperdica pixels.
- Proporcionalidade visual imediata entre topicos.
- Dimensao de cor carrega segunda metrica (impacto) sem dominar.
            """
        )

    with st.expander("💰 Visao 5 — Barras de refaturamento por causa"):
        st.markdown(
            """
**Pergunta respondida:** *onde agir tem maior retorno financeiro direto?*

**Pipeline:**
1. `flag_resolvido_com_refaturamento` vem do Silver como boolean normalizado.
2. `refaturamento_by_cause(frame, limit=10)` faz `groupby(causa).agg(nunique(ordem), mean(flag))` e ordena por **taxa desc**.
3. Filtro `qtd_erros > 0` evita divisao por zero em causas raras.
4. `plotly.express.bar` com `text` exibindo volume absoluto sobre cada barra.

**Leitura combinada:**
- **Alta barra + cor clara** = alvo prioritario (muito volume *e* alto impacto).
- **Alta barra + cor escura** = raro mas quase sempre gera retificacao.
- Taxa formatada como `%` (eixo Y) + volume absoluto (rotulos) → duas grandezas no mesmo grafico.
            """
        )

    with st.expander("🔐 Mascaramento PII aplicado nas amostras"):
        st.markdown(
            """
**Problema:** textos livres contem telefones, CEPs, e-mails, nomes, enderecos, protocolos.

**Solucao implementada:**
1. Regex de sanitizacao rodados no Silver (layer `erro_leitura_normalizer`):
   - Telefone: `\\b\\d{2}\\s?\\d{4,5}-?\\d{4}\\b` → `<TEL>`
   - CEP: `\\b\\d{5}-?\\d{3}\\b` → `<CEP>`
   - E-mail: regex padrao RFC-simplificada → `<EMAIL>`
   - Protocolo: sequencias numericas longas → `<PROT>`
2. Amostras por topico passam por `_taxonomy_example(item)` antes de render.
3. `instalacao` nunca aparece em texto — apenas `sha256(instalacao)[:12]`.

**Garantia:** o dashboard e auditavel — nenhum campo livre cru e exibido em nenhuma das 4 visoes principais.
            """
        )

    with st.expander("⚙ Stack tecnica resumida"):
        st.markdown(
            """
| Camada | Ferramenta | Papel |
|---|---|---|
| Storage | MinIO + Iceberg | Bronze/Silver/Gold (futuro) |
| Transformacao | pandas + dbt Core | Silver via Python, Gold via SQL |
| Embeddings | sentence-transformers | MiniLM multilingual, CPU-only |
| Topic modeling | BERTopic (UMAP + HDBSCAN) | Clusters nao-supervisionados |
| Classificador | Keyword + LightGBM (fallback) | Causa canonica |
| Dashboard | Streamlit + Plotly Express | Esta interface |
| Orquestracao | Airflow | Retreino semanal + ingestao diaria |
| Proxy reverso | Caddy / Cloudflare Tunnel | Exposicao publica (ver docs) |

**Hardware-aware:** tudo roda em notebook 16GB RAM / i7-1185G7 / sem GPU.
            """
        )


def _inject_style() -> None:
    st.markdown(
        """
        <style>
        :root {
            --enel-blue: #0F4C81;
            --enel-blue-dark: #0B3A63;
            --enel-blue-light: #1F6FB2;
            --enel-green: #00813E;
            --enel-orange: #F7941D;
            --enel-amber: #FBB040;
            --enel-red: #E4002B;
            --ink-900: #1A1A1A;
            --ink-700: #3F4A55;
            --ink-500: #6B7680;
            --surface-0: #FFFFFF;
            --surface-1: #F6F9FC;
            --surface-2: #E6ECF2;
        }
        .stApp {
            background:
              radial-gradient(circle at 10% 6%, rgba(15, 76, 129, .10), transparent 28rem),
              radial-gradient(circle at 90% 4%, rgba(0, 129, 62, .08), transparent 24rem),
              linear-gradient(180deg, #FFFFFF 0%, #F6F9FC 55%, #E6ECF2 100%);
            color: var(--ink-900);
        }
        .hero {
            padding: 2rem 2rem 1.4rem;
            border-radius: 28px;
            background:
              linear-gradient(135deg, var(--enel-blue) 0%, var(--enel-blue-dark) 60%, #072A4A 100%),
              repeating-linear-gradient(45deg, rgba(255,255,255,.05) 0 1px, transparent 1px 12px);
            color: #FFFFFF;
            margin-bottom: 1rem;
            box-shadow: 0 24px 60px rgba(15, 76, 129, .32);
            border-left: 6px solid var(--enel-orange);
        }
        .hero h1 {
            font-size: clamp(2.1rem, 5vw, 4.7rem);
            line-height: .95;
            letter-spacing: -.04em;
            margin: .2rem 0 .8rem;
            color: #FFFFFF;
        }
        .eyebrow {
            text-transform: uppercase;
            letter-spacing: .16em;
            font-weight: 700;
            color: var(--enel-orange);
            margin: 0;
        }
        .subtitle {
            max-width: 58rem;
            font-size: 1.08rem;
            color: #E6ECF2;
        }
        .metric-card {
            min-height: 140px;
            padding: 1rem 1.1rem;
            border: 1px solid var(--surface-2);
            border-radius: 18px;
            background: var(--surface-0);
            box-shadow: 0 8px 24px rgba(15, 76, 129, .08);
            border-top: 4px solid var(--enel-blue);
        }
        .metric-card span {
            display: block;
            color: var(--ink-500);
            font-size: .78rem;
            text-transform: uppercase;
            letter-spacing: .08em;
            font-weight: 700;
        }
        .metric-card strong {
            display: block;
            font-size: 2rem;
            letter-spacing: -.02em;
            color: var(--enel-blue);
            margin-top: .35rem;
            font-weight: 700;
        }
        .metric-card small {
            color: var(--ink-700);
        }
        [data-testid="stMetricValue"] {
            color: var(--enel-blue);
            font-weight: 700;
        }
        [data-testid="stMetricLabel"] {
            color: var(--ink-700);
            font-weight: 600;
        }
        [data-testid="stMetricDelta"] svg { fill: var(--enel-green); }
        h1, h2, h3, h4 { color: var(--ink-900); }
        .stTabs [data-baseweb="tab-list"] {
            gap: .35rem;
            border-bottom: 2px solid var(--surface-2);
        }
        .stTabs [data-baseweb="tab"] {
            border-radius: 12px 12px 0 0;
            padding: .6rem 1.1rem;
            background: var(--surface-1);
            font-weight: 600;
            color: var(--ink-700);
            border: 1px solid transparent;
        }
        .stTabs [data-baseweb="tab"]:hover {
            background: var(--surface-2);
            color: var(--enel-blue);
        }
        .stTabs [aria-selected="true"] {
            background: var(--enel-blue) !important;
            color: #FFFFFF !important;
            border-color: var(--enel-blue) !important;
            box-shadow: 0 -2px 0 var(--enel-orange) inset;
        }
        section[data-testid="stSidebar"] {
            background: var(--surface-0);
            border-right: 1px solid var(--surface-2);
        }
        .stButton > button {
            background: var(--enel-blue);
            color: #FFFFFF;
            border: none;
            font-weight: 600;
        }
        .stButton > button:hover {
            background: var(--enel-blue-light);
            color: #FFFFFF;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
