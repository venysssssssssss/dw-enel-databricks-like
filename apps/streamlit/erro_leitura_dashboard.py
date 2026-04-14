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
    compute_kpis,
    load_dashboard_frame,
    monthly_volume,
    refaturamento_by_cause,
    region_cause_matrix,
    root_cause_distribution,
    safe_topic_taxonomy_for_display,
    topic_distribution,
)


PALETTE = {
    "primary": "#104C43",
    "accent": "#D97706",
    "ce": "#D97706",
    "sp": "#104C43",
    "muted": "#7C6A46",
}


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

    tab_overview, tab_patterns, tab_impact, tab_taxonomy, tab_gov, tab_edu = st.tabs(
        [
            "📈 Ritmo Operacional",
            "🗺 Padroes & Concentracoes",
            "💰 Impacto de Refaturamento",
            "🧬 Taxonomia Descoberta",
            "🛡 Governanca",
            "🎓 Sessao Educacional",
        ]
    )

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
        .stApp {
            background:
              radial-gradient(circle at 12% 8%, rgba(245, 158, 11, .22), transparent 28rem),
              radial-gradient(circle at 88% 4%, rgba(20, 83, 45, .18), transparent 24rem),
              linear-gradient(180deg, #F8F3EA 0%, #F4EEE3 45%, #ECE2D1 100%);
            color: #1f2933;
        }
        .hero {
            padding: 2rem 2rem 1.4rem;
            border-radius: 28px;
            background:
              linear-gradient(135deg, rgba(16, 76, 67, .94), rgba(67, 56, 36, .92)),
              repeating-linear-gradient(45deg, rgba(255,255,255,.08) 0 1px, transparent 1px 12px);
            color: #fff8ec;
            margin-bottom: 1rem;
            box-shadow: 0 24px 70px rgba(67, 56, 36, .23);
        }
        .hero h1 {
            font-size: clamp(2.1rem, 5vw, 4.7rem);
            line-height: .95;
            letter-spacing: -.06em;
            margin: .2rem 0 .8rem;
        }
        .eyebrow {
            text-transform: uppercase;
            letter-spacing: .16em;
            font-weight: 700;
            color: #FBBF24;
            margin: 0;
        }
        .subtitle {
            max-width: 58rem;
            font-size: 1.08rem;
            color: #FDECC8;
        }
        .metric-card {
            min-height: 140px;
            padding: 1rem;
            border: 1px solid rgba(67, 56, 36, .18);
            border-radius: 22px;
            background: rgba(255, 250, 241, .82);
            box-shadow: 0 12px 32px rgba(67, 56, 36, .12);
        }
        .metric-card span {
            display: block;
            color: #6B5B3D;
            font-size: .78rem;
            text-transform: uppercase;
            letter-spacing: .08em;
            font-weight: 700;
        }
        .metric-card strong {
            display: block;
            font-size: 2rem;
            letter-spacing: -.04em;
            color: #104C43;
            margin-top: .35rem;
        }
        .metric-card small {
            color: #7C6A46;
        }
        [data-testid="stMetricValue"] {
            color: #104C43;
        }
        .stTabs [data-baseweb="tab-list"] {
            gap: .4rem;
        }
        .stTabs [data-baseweb="tab"] {
            border-radius: 14px 14px 0 0;
            padding: .6rem 1.1rem;
            background: rgba(255, 250, 241, .55);
            font-weight: 600;
        }
        .stTabs [aria-selected="true"] {
            background: #104C43 !important;
            color: #fff8ec !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
