"""RAG data cards generated from the same data plane views used by BI."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from src.rag.ingestion import Chunk, _approx_tokens

if TYPE_CHECKING:
    import pandas as pd

    from src.data_plane.store import DataStore


@dataclass(frozen=True, slots=True)
class DataCard:
    anchor: str
    title: str
    body: str
    region: str = "CE+SP"


def build_data_cards(
    store: DataStore,
    regional_scope: Literal["CE", "SP", "CE+SP"] = "CE+SP",
) -> list[Chunk]:
    version = store.version()
    if not version.sources:
        return []
    scope = _normalize_scope(regional_scope)
    scope_filters = _scope_filters(scope)
    by_region = store.aggregate("by_region")
    top_assuntos = store.aggregate("top_assuntos", scope_filters)
    top_causas = store.aggregate("top_causas", scope_filters)
    refaturamento = store.aggregate("refaturamento_summary", scope_filters)
    monthly = store.aggregate("monthly_volume", scope_filters)
    groups = store.aggregate("by_group", scope_filters)
    top_installations_regional = store.aggregate("top_instalacoes_por_regional", scope_filters)
    top_installations_digitacao = store.aggregate("top_instalacoes_digitacao", scope_filters)
    sazonalidade = store.aggregate("sazonalidade_reclamacoes", scope_filters)
    reincidencia_assunto = store.aggregate("reincidencia_por_assunto", scope_filters)
    playbook = store.aggregate("playbook_dificuldade_acoes", scope_filters)
    sp_causa_obs = store.aggregate("sp_causa_observacoes", {"regiao": ["SP"]})
    sp_profile = store.aggregate("sp_perfil_assunto_lider", {"regiao": ["SP"]})
    sp_tipos_medidor = store.aggregate("sp_tipos_medidor", {"regiao": ["SP"]})
    sp_tipos_medidor_digitacao = store.aggregate("sp_tipos_medidor_digitacao", {"regiao": ["SP"]})
    sp_causas_por_tipo = store.aggregate("sp_causas_por_tipo_medidor", {"regiao": ["SP"]})
    motivos_taxonomia = store.aggregate("motivos_taxonomia", scope_filters)
    frame = store.load_silver(include_total=False)

    cards = [
        _overview_card(store.aggregate("overview", scope_filters), region=scope),
        _top_assunto_card(top_assuntos, region=scope),
        _top_causa_card(top_causas, region=scope),
        _refaturamento_card(
            refaturamento,
            by_region=store.aggregate("by_region", scope_filters),
            top_assuntos=top_assuntos,
            region=scope,
        ),
        _monthly_card(monthly, region=scope),
        _grupo_card(groups, region=scope),
        _instalacoes_por_regional_card(top_installations_regional, region=scope),
        _instalacoes_digitacao_card(top_installations_digitacao, region=scope),
        _sazonalidade_card(sazonalidade, region=scope),
        _reincidencia_por_assunto_card(reincidencia_assunto, region=scope),
        _playbook_card(playbook, region=scope),
        _motivos_taxonomia_card(motivos_taxonomia, region=scope),
        _data_quality_notes_card(frame),
    ]
    if scope in {"CE", "CE+SP"}:
        cards.append(
            _regional_card(
                "CE",
                by_region,
                store.aggregate("top_assuntos", {"regiao": ["CE"]}),
                store.aggregate("top_causas", {"regiao": ["CE"]}),
                frame,
            )
        )
    if scope in {"SP", "CE+SP"}:
        cards.append(
            _regional_card(
                "SP",
                by_region,
                store.aggregate("top_assuntos", {"regiao": ["SP"]}),
                store.aggregate("top_causas", {"regiao": ["SP"]}),
                frame,
            )
        )
    if scope == "CE+SP":
        cards.extend(
            [
                _ce_vs_sp_causas_card(store),
                _ce_vs_sp_refaturamento_card(by_region),
                _ce_vs_sp_mensal_card(store.aggregate("monthly_volume")),
            ]
        )
    if scope in {"CE", "CE+SP"}:
        # Cards dedicados às reclamações TOTAIS de CE (167k ordens, 20+ assuntos)
        # — o usuário pode perguntar sobre o universo completo, não só o subset
        # rotulado de erro_leitura.
        cards.extend(_ce_total_complaints_cards(store))
        cards.extend(_ce_mvp_extra_cards(store))
    if scope in {"SP", "CE+SP"}:
        cards.extend(_sp_n1_cards(store))
        cards.append(_sp_causa_observacoes_card(sp_causa_obs))
        cards.append(_sp_perfil_assunto_lider_card(sp_profile))
        cards.append(_sp_tipos_medidor_card(sp_tipos_medidor))
        cards.append(_sp_tipos_medidor_digitacao_card(sp_tipos_medidor_digitacao))
        cards.append(_sp_causas_por_tipo_medidor_card(sp_causas_por_tipo))

    source = store.silver_path.as_posix()
    return [
        _chunk_from_card(card, source_path=source, dataset_version=version.hash)
        for card in cards
    ]


def _chunk_from_card(card: DataCard, *, source_path: str, dataset_version: str) -> Chunk:
    text = f"# {card.title}\n\n{card.body}".strip()
    chunk_key = f"{source_path}::{dataset_version}::{card.anchor}::{text[:120]}"
    chunk_id = hashlib.sha256(chunk_key.encode()).hexdigest()[:16]
    return Chunk(
        chunk_id=chunk_id,
        text=text,
        source_path=source_path,
        section=card.title,
        doc_type="data",
        sprint_id="",
        token_count=_approx_tokens(text),
        anchor=card.anchor,
        dataset_version=dataset_version,
        region=card.region,
        scope="regional",
        data_source="silver.erro_leitura_normalizado",
    )


def _normalize_scope(scope: str) -> Literal["CE", "SP", "CE+SP"]:
    normalized = (scope or "CE+SP").strip().upper()
    if normalized in {"CE", "SP", "CE+SP"}:
        return normalized  # type: ignore[return-value]
    return "CE+SP"


def _scope_filters(scope: Literal["CE", "SP", "CE+SP"]) -> dict[str, list[str]]:
    if scope in {"CE", "SP"}:
        return {"regiao": [scope]}
    return {"regiao": ["CE", "SP"]}


def _fmt_pct(value: float) -> str:
    return f"{100.0 * value:.1f}%"


def _fmt_share(part: float, total: float) -> str:
    return "0.0%" if total == 0 else f"{100.0 * part / total:.1f}%"


def _fmt_n(value: int | float) -> str:
    return f"{int(value):,}".replace(",", ".")


def _total(overview: pd.DataFrame) -> int:
    if overview.empty or "total_registros" not in overview.columns:
        return 0
    return int(overview["total_registros"].iloc[0])


def _overview_card(overview: pd.DataFrame, *, region: str) -> DataCard:
    if overview.empty:
        return DataCard(
            "visao-geral",
            "Visão geral das reclamações CE + SP",
            "Sem dados disponíveis.",
            region=region,
        )
    row = overview.iloc[0]
    body = (
        f"Base de reclamações ENEL consolidada com **{_fmt_n(row['total_registros'])} ordens**. "
        f"O dataset cobre **{_fmt_n(row['regioes'])} regiões**, "
        f"**{_fmt_n(row['topicos'])} tópicos** e "
        f"**{_fmt_pct(float(row['taxa_refaturamento']))}** de taxa de refaturamento. "
        f"A cobertura de causa-raiz informada pela origem é "
        f"**{_fmt_pct(float(row['taxa_rotulo_origem']))}**."
    )
    return DataCard("visao-geral", "Visão geral das reclamações CE + SP", body, region=region)


def _by_region_cards(by_region: pd.DataFrame, *, total: int) -> list[DataCard]:
    cards: list[DataCard] = []
    for row in by_region.itertuples(index=False):
        region = str(row.regiao)
        count = int(row.qtd_ordens)
        body = (
            f"Região **{region}** concentra **{_fmt_n(count)} ordens** "
            f"({_fmt_share(count, total)} do total filtrado). "
            f"Refaturamento resolve **{_fmt_pct(float(row.taxa_refaturamento))}** dos casos, "
            f"com **{_fmt_n(row.causas_rotuladas)}** ordens com causa-raiz rotulada."
        )
        cards.append(DataCard(f"regiao-{region.lower()}", f"Reclamações na região {region}", body))
    return cards


def _top_assunto_card(top: pd.DataFrame, *, region: str) -> DataCard:
    lines = ["Os **assuntos mais frequentes** no dataset analítico atual:", ""]
    for row in top.itertuples(index=False):
        lines.append(
            f"- **{row.assunto}**: {_fmt_n(row.qtd_ordens)} "
            f"ordens ({_fmt_pct(row.percentual)})"
        )
    return DataCard("top-assuntos", "Top assuntos de reclamação", "\n".join(lines), region=region)


def _top_causa_card(top: pd.DataFrame, *, region: str) -> DataCard:
    lines = ["As **causas canônicas mais prevalentes** na base analítica:", ""]
    for row in top.itertuples(index=False):
        label = str(row.causa_canonica).strip()[:200]
        lines.append(
            f"- **{label}**: {_fmt_n(row.qtd_ordens)} "
            f"ordens ({_fmt_pct(row.percentual)})"
        )
    return DataCard(
        "top-causas-raiz",
        "Top causas-raiz identificadas pela operação",
        "\n".join(lines),
        region=region,
    )


def _refaturamento_card(
    summary: pd.DataFrame,
    by_region: pd.DataFrame,
    top_assuntos: pd.DataFrame,
    *,
    region: str,
) -> DataCard:
    if summary.empty:
        return DataCard(
            "refaturamento",
            "Impacto de refaturamento como desfecho",
            "Sem dados disponíveis.",
            region=region,
        )
    row = summary.iloc[0]
    lines = [
        f"**Refaturamento** foi o desfecho em {_fmt_n(row['refaturadas'])} "
        f"({_fmt_pct(float(row['taxa_refaturamento']))}) das {_fmt_n(row['total'])} ordens totais.",
        "",
        "**Distribuição por região**:",
    ]
    for region_row in by_region.itertuples(index=False):
        lines.append(
            f"- {region_row.regiao}: {_fmt_n(region_row.ordens_refaturadas)} "
            "ordens resolvidas com refaturamento"
        )
    lines.append("")
    lines.append("**Assuntos mais relevantes para investigação**:")
    for assunto in top_assuntos.head(6).itertuples(index=False):
        lines.append(f"- {assunto.assunto}: {_fmt_n(assunto.qtd_ordens)}")
    return DataCard(
        "refaturamento",
        "Impacto de refaturamento como desfecho",
        "\n".join(lines),
        region=region,
    )


def _monthly_card(monthly: pd.DataFrame, *, region: str) -> DataCard:
    if monthly.empty:
        return DataCard(
            "evolucao-mensal",
            "Evolução mensal de reclamações",
            "(sem dados de data disponíveis)",
            region=region,
        )
    total_by_month = monthly.groupby("mes_ingresso", as_index=False).agg(
        qtd_erros=("qtd_erros", "sum")
    )
    max_val = int(total_by_month["qtd_erros"].max())
    lines = ["**Evolução mensal** do volume de reclamações:", ""]
    for row in total_by_month.sort_values("mes_ingresso").itertuples(index=False):
        month = row.mes_ingresso
        label = month.strftime("%Y-%m") if hasattr(month, "strftime") else str(month)[:7]
        bar = "#" * max(1, int(int(row.qtd_erros) / max(max_val, 1) * 20))
        lines.append(f"- `{label}`: {_fmt_n(row.qtd_erros)} {bar}")
    peak = total_by_month.sort_values("qtd_erros", ascending=False).iloc[0]
    peak_month = peak["mes_ingresso"]
    peak_label = (
        peak_month.strftime("%Y-%m") if hasattr(peak_month, "strftime") else str(peak_month)[:7]
    )
    lines.append("")
    lines.append(f"Pico em **{peak_label}** com {_fmt_n(peak['qtd_erros'])} ordens.")
    return DataCard(
        "evolucao-mensal",
        "Evolução mensal de reclamações",
        "\n".join(lines),
        region=region,
    )


def _grupo_card(groups: pd.DataFrame, *, region: str) -> DataCard:
    lines = ["Distribuição por **grupo tarifário** no dataset analítico atual:", ""]
    for row in groups.itertuples(index=False):
        lines.append(f"- **{row.grupo}**: {_fmt_n(row.qtd_ordens)} ({_fmt_pct(row.percentual)})")
    return DataCard(
        "grupo-tarifario",
        "Distribuição por grupo tarifário",
        "\n".join(lines),
        region=region,
    )


def _instalacoes_por_regional_card(data: pd.DataFrame, *, region: str) -> DataCard:
    if data.empty:
        return DataCard(
            "instalacoes-por-regional",
            "Instalações com mais reclamações por regional",
            "Sem dados de instalação disponíveis por regional.",
            region=region,
        )
    lines = ["Instalações com maior volume de reclamações por regional:", ""]
    for reg, group in data.groupby("regiao"):
        lines.append(f"**{reg}**")
        for row in group.itertuples(index=False):
            meter = (
                f" | medidor: {row.tipo_medidor_dominante}"
                if getattr(row, "tipo_medidor_dominante", "")
                else ""
            )
            lines.append(
                f"- `{row.instalacao}`: {_fmt_n(row.qtd_ordens)} ordens "
                f"(assunto líder: {row.assunto_top}){meter}"
            )
        lines.append("")
    return DataCard(
        "instalacoes-por-regional",
        "Instalações com mais reclamações por regional",
        "\n".join(lines).strip(),
        region=region,
    )


def _instalacoes_digitacao_card(data: pd.DataFrame, *, region: str) -> DataCard:
    if data.empty:
        return DataCard(
            "instalacoes-digitacao",
            "Instalações com mais ocorrências de digitação",
            "Sem dados de instalação para ocorrências com causa de digitação.",
            region=region,
        )
    lines = ["Instalações com maior volume de reclamações ligadas à digitação:", ""]
    for row in data.head(20).itertuples(index=False):
        meter = (
            f" | medidor: {row.tipo_medidor_dominante}"
            if getattr(row, "tipo_medidor_dominante", "")
            else ""
        )
        lines.append(
            f"- {row.regiao} | `{row.instalacao}`: {_fmt_n(row.qtd_ordens)} ordens "
            f"(assunto líder: {row.assunto_top}){meter}"
        )
    return DataCard(
        "instalacoes-digitacao",
        "Instalações com mais ocorrências de digitação",
        "\n".join(lines),
        region=region,
    )


def _sazonalidade_card(data: pd.DataFrame, *, region: str) -> DataCard:
    if data.empty:
        return DataCard(
            "sazonalidade-ce-sp",
            "Sazonalidade das reclamações",
            "Sem dados mensais suficientes para sazonalidade.",
            region=region,
        )
    lines = ["Sazonalidade por regional (pico mensal vs média):", ""]
    for row in data.itertuples(index=False):
        lines.append(
            f"- {row.regiao}: pico em **{row.mes_pico}** com {_fmt_n(row.qtd_pico)} ordens "
            f"(índice sazonal {row.indice_sazonal_pico:.2f}x da média)."
        )
    return DataCard(
        "sazonalidade-ce-sp",
        "Sazonalidade das reclamações",
        "\n".join(lines),
        region=region,
    )


def _reincidencia_por_assunto_card(data: pd.DataFrame, *, region: str) -> DataCard:
    if data.empty:
        return DataCard(
            "reincidencia-por-assunto",
            "Reincidência de reclamações por assunto",
            "Sem dados de reincidência por assunto.",
            region=region,
        )
    lines = ["Reincidência de instalações por assunto (top):", ""]
    for row in data.head(12).itertuples(index=False):
        lines.append(
            f"- **{row.assunto}**: {_fmt_n(row.qtd_instalacoes_reincidentes)} instalações "
            f"reincidentes de {_fmt_n(row.qtd_instalacoes)} "
            f"({100.0 * float(row.taxa_reincidencia):.1f}%)."
        )
    return DataCard(
        "reincidencia-por-assunto",
        "Reincidência de reclamações por assunto",
        "\n".join(lines),
        region=region,
    )


def _playbook_card(data: pd.DataFrame, *, region: str) -> DataCard:
    if data.empty:
        return DataCard(
            "playbook-acoes-cliente",
            "Dificuldade principal e medidas recomendadas",
            "Sem sinal suficiente para sugerir medidas operacionais.",
            region=region,
        )
    row = data.iloc[0]
    body = (
        f"Dificuldade principal observada: **{row['dificuldade_principal']}**.\n\n"
        f"Medida recomendada: **{row['medida_recomendada']}**.\n"
        f"Prioridade sugerida: **{row['prioridade']}**."
    )
    return DataCard(
        "playbook-acoes-cliente",
        "Dificuldade principal e medidas recomendadas",
        body,
        region=region,
    )


def _regional_card(
    region: Literal["CE", "SP"],
    by_region: pd.DataFrame,
    top_assuntos: pd.DataFrame,
    top_causas: pd.DataFrame,
    frame: pd.DataFrame,
) -> DataCard:
    row = by_region.loc[by_region["regiao"].astype(str) == region]
    if row.empty:
        return DataCard(
            f"regiao-{region.lower()}",
            f"Reclamações na região {region}",
            "Sem dados disponíveis para a regional.",
            region=region,
        )
    item = row.iloc[0]
    major_assunto = "(não informado)"
    assunto_row = top_assuntos.iloc[0] if not top_assuntos.empty else None
    if assunto_row is not None:
        major_assunto = str(assunto_row.get("assunto", "(não informado)"))

    major_causa = "(não informado)"
    causa_row = top_causas.iloc[0] if not top_causas.empty else None
    if causa_row is not None:
        major_causa = str(causa_row.get("causa_canonica", "(não informado)"))

    coverage = _coverage_window(frame, region)
    lines = [
        f"Regional **{region}** com **{_fmt_n(item['qtd_ordens'])} ordens** e "
        f"taxa de refaturamento de **{_fmt_pct(float(item['taxa_refaturamento']))}**.",
        f"Ordens refaturadas: **{_fmt_n(item['ordens_refaturadas'])}**.",
        f"Causas rotuladas: **{_fmt_n(item['causas_rotuladas'])}**.",
        f"Top assunto: **{major_assunto}**. Top causa: **{major_causa}**.",
        (
            "Cobertura temporal: "
            f"**{coverage['start']} → {coverage['end']}** ({_fmt_n(coverage['days'])} dias)."
            if coverage["days"] > 0
            else "Cobertura temporal indisponível para a regional."
        ),
    ]
    if region == "SP":
        lines.append(
            "Aviso de qualidade: SP possui viés elevado para ERRO_LEITURA e "
            "taxa de refaturamento resolvido zerada "
            "[fonte: data/silver/erro_leitura_normalizado.csv#data-quality-notes]."
        )
    return DataCard(
        f"regiao-{region.lower()}",
        f"Reclamações na região {region}",
        "\n".join(lines),
        region=region,
    )


def _ce_vs_sp_causas_card(store: DataStore) -> DataCard:
    ce = store.aggregate("top_causas", {"regiao": ["CE"]}).head(5)
    sp = store.aggregate("top_causas", {"regiao": ["SP"]}).head(5)
    lines = ["Top-5 causas canônicas comparando **CE x SP**:", ""]
    lines.append("**CE**")
    for row in ce.itertuples(index=False):
        lines.append(
            f"- {row.causa_canonica}: "
            f"{_fmt_n(row.qtd_ordens)} ({_fmt_pct(row.percentual)})"
        )
    lines.append("")
    lines.append("**SP**")
    for row in sp.itertuples(index=False):
        lines.append(
            f"- {row.causa_canonica}: "
            f"{_fmt_n(row.qtd_ordens)} ({_fmt_pct(row.percentual)})"
        )
    return DataCard(
        "ce-vs-sp-causas",
        "Comparativo CE vs SP por causas",
        "\n".join(lines),
        region="CE+SP",
    )


def _ce_vs_sp_refaturamento_card(by_region: pd.DataFrame) -> DataCard:
    table = by_region.set_index("regiao") if not by_region.empty else by_region
    ce_rate = float(table.loc["CE", "taxa_refaturamento"]) if "CE" in table.index else 0.0
    sp_rate = float(table.loc["SP", "taxa_refaturamento"]) if "SP" in table.index else 0.0
    ce_ref = int(table.loc["CE", "ordens_refaturadas"]) if "CE" in table.index else 0
    sp_ref = int(table.loc["SP", "ordens_refaturadas"]) if "SP" in table.index else 0
    body = (
        "Comparativo de refaturamento resolvido:\n\n"
        f"- CE: {_fmt_pct(ce_rate)} ({_fmt_n(ce_ref)} ordens)\n"
        f"- SP: {_fmt_pct(sp_rate)} ({_fmt_n(sp_ref)} ordens)\n\n"
        "SP deve ser interpretada com caveat de viés "
        "[fonte: data/silver/erro_leitura_normalizado.csv#data-quality-notes]."
    )
    return DataCard(
        "ce-vs-sp-refaturamento",
        "Comparativo CE vs SP de refaturamento",
        body,
        region="CE+SP",
    )


def _ce_vs_sp_mensal_card(monthly: pd.DataFrame) -> DataCard:
    if monthly.empty:
        return DataCard(
            "ce-vs-sp-mensal",
            "Série mensal CE vs SP",
            "Sem dados mensais disponíveis para comparação.",
            region="CE+SP",
        )
    lines = ["Série mensal comparativa CE x SP:", ""]
    pivot = (
        monthly.pivot_table(
            index="mes_ingresso",
            columns="regiao",
            values="qtd_erros",
            aggfunc="sum",
            fill_value=0,
        )
        .reset_index()
        .sort_values("mes_ingresso")
    )
    for row in pivot.itertuples(index=False):
        if hasattr(row.mes_ingresso, "strftime"):
            month = row.mes_ingresso.strftime("%Y-%m")
        else:
            month = str(row.mes_ingresso)[:7]
        ce = getattr(row, "CE", 0)
        sp = getattr(row, "SP", 0)
        lines.append(f"- {month}: CE={_fmt_n(ce)} | SP={_fmt_n(sp)}")
    return DataCard(
        "ce-vs-sp-mensal",
        "Série mensal CE vs SP",
        "\n".join(lines),
        region="CE+SP",
    )


_CE_TOTAL_FILTERS: dict[str, list[str]] = {
    "regiao": ["CE"],
    "tipo_origem": ["reclamacao_total"],
}


def _ce_total_complaints_cards(store: DataStore) -> list[DataCard]:
    """Cards sobre o universo completo de reclamações CE (reclamacao_total).

    O dataset CE tem duas camadas: (a) 4,9k registros rotulados de erro de
    leitura (usados no dashboard/ML) e (b) 167k reclamações totais 2025-01 →
    2026-03 cobrindo 20+ assuntos reais (REFATURAMENTO PRODUTOS, CRITICA GRUPO
    B, VARIAÇÃO DE CONSUMO etc.). Estes cards expõem (b) — que é o que o
    usuário pergunta quando cita "reclamações em CE".
    """
    overview = store.aggregate("overview", _CE_TOTAL_FILTERS, include_total=True)
    assuntos = store.aggregate("top_assuntos", _CE_TOTAL_FILTERS, include_total=True)
    refat = store.aggregate("refaturamento_summary", _CE_TOTAL_FILTERS, include_total=True)
    monthly = store.aggregate("monthly_volume", _CE_TOTAL_FILTERS, include_total=True)
    groups = store.aggregate("by_group", _CE_TOTAL_FILTERS, include_total=True)
    causas = store.aggregate("top_causas", _CE_TOTAL_FILTERS, include_total=True)
    assunto_causa = store.aggregate("ce_total_assunto_causa", _CE_TOTAL_FILTERS, include_total=True)

    return [
        _ce_total_overview_card(overview),
        _ce_total_assuntos_card(assuntos),
        _ce_total_refaturamento_card(refat, assuntos),
        _ce_total_assunto_causa_card(assunto_causa),
        _ce_total_evolucao_card(monthly),
        _ce_total_grupo_card(groups),
        _ce_total_causas_card(causas),
    ]


def _ce_total_overview_card(overview: pd.DataFrame) -> DataCard:
    if overview.empty:
        return DataCard(
            "ce-reclamacoes-totais-overview",
            "Reclamações totais CE — visão geral",
            "Sem dados disponíveis.",
            region="CE",
        )
    row = overview.iloc[0]
    body = (
        f"Em **CE**, o dataset contém **{_fmt_n(row['total_registros'])} reclamações totais** "
        f"(tipo_origem=reclamacao_total, cobertura 2025-01 → 2026-03). "
        f"**{_fmt_pct(float(row['taxa_refaturamento']))}** foram resolvidas com refaturamento. "
        f"**{_fmt_pct(float(row['taxa_rotulo_origem']))}** têm causa-raiz rotulada pela operação."
    )
    return DataCard(
        "ce-reclamacoes-totais-overview",
        "Reclamações totais CE — visão geral",
        body,
        region="CE",
    )


def _ce_total_assuntos_card(assuntos: pd.DataFrame) -> DataCard:
    if assuntos.empty:
        return DataCard(
            "ce-reclamacoes-totais-assuntos",
            "CE — top assuntos (reclamações totais)",
            "Sem dados de assunto disponíveis.",
            region="CE",
        )
    top = assuntos.iloc[0]
    header = (
        f"O principal assunto das reclamações em CE é **{top.assunto}** com "
        f"**{_fmt_n(top.qtd_ordens)}** ordens ({_fmt_pct(top.percentual)})."
    )
    lines = [
        header,
        "",
        "**Top assuntos das reclamações totais em CE** "
        "(universo de 167,6k ordens):",
        "",
    ]
    for row in assuntos.itertuples(index=False):
        lines.append(
            f"- **{row.assunto}**: {_fmt_n(row.qtd_ordens)} "
            f"({_fmt_pct(row.percentual)})"
        )
    return DataCard(
        "ce-reclamacoes-totais-assuntos",
        "CE — top assuntos (reclamações totais)",
        "\n".join(lines),
        region="CE",
    )


def _ce_total_refaturamento_card(
    summary: pd.DataFrame, assuntos: pd.DataFrame
) -> DataCard:
    if summary.empty:
        return DataCard(
            "ce-reclamacoes-totais-refaturamento",
            "CE — refaturamento nas reclamações totais",
            "Sem dados disponíveis.",
            region="CE",
        )
    row = summary.iloc[0]
    lines = [
        f"Em CE, **{_fmt_n(row['refaturadas'])}** "
        f"({_fmt_pct(float(row['taxa_refaturamento']))}) "
        f"das {_fmt_n(row['total'])} reclamações totais foram "
        "**resolvidas com refaturamento**.",
        "",
        "**Assuntos com maior volume associado ao tema**:",
    ]
    refat_like = assuntos[
        assuntos["assunto"].astype(str).str.contains("REFAT", case=False, na=False)
    ].head(6)
    for row in refat_like.itertuples(index=False):
        lines.append(
            f"- {row.assunto}: {_fmt_n(row.qtd_ordens)} "
            f"({_fmt_pct(row.percentual)})"
        )
    return DataCard(
        "ce-reclamacoes-totais-refaturamento",
        "CE — refaturamento nas reclamações totais",
        "\n".join(lines),
        region="CE",
    )


def _ce_total_assunto_causa_card(data: pd.DataFrame) -> DataCard:
    if data.empty:
        return DataCard(
            "ce-reclamacoes-totais-assunto-causa",
            "CE — causas por assunto (reclamações totais)",
            "Sem dados suficientes para explicabilidade assunto→causa em CE total.",
            region="CE",
        )
    lines = [
        "Explicabilidade CE (reclamações totais): principais causas dentro dos assuntos líderes.",
        "",
    ]
    ordered = data.sort_values(["rank_assunto", "rank_causa"]).reset_index(drop=True)
    for assunto, group in ordered.groupby("assunto", sort=False):
        total = int(group.iloc[0]["qtd_assunto"])
        lines.append(f"**{assunto}** ({_fmt_n(total)} ordens):")
        for row in group.itertuples(index=False):
            lines.append(
                f"- {int(row.rank_causa)}. {row.causa_canonica}: "
                f"{_fmt_n(row.qtd_ordens)} "
                f"({_fmt_pct(float(row.percentual_no_assunto))} no assunto)"
            )
        lines.append("")
    return DataCard(
        "ce-reclamacoes-totais-assunto-causa",
        "CE — causas por assunto (reclamações totais)",
        "\n".join(lines).strip(),
        region="CE",
    )


def _ce_total_evolucao_card(monthly: pd.DataFrame) -> DataCard:
    if monthly.empty:
        return DataCard(
            "ce-reclamacoes-totais-evolucao",
            "CE — evolução mensal das reclamações totais",
            "Sem dados mensais disponíveis.",
            region="CE",
        )
    agg = monthly.groupby("mes_ingresso", as_index=False).agg(
        qtd=("qtd_erros", "sum")
    )
    max_val = int(agg["qtd"].max()) or 1
    lines = ["**Evolução mensal das reclamações totais em CE**:", ""]
    for row in agg.sort_values("mes_ingresso").itertuples(index=False):
        month = row.mes_ingresso
        label = (
            month.strftime("%Y-%m") if hasattr(month, "strftime") else str(month)[:7]
        )
        bar = "#" * max(1, int(int(row.qtd) / max_val * 20))
        lines.append(f"- `{label}`: {_fmt_n(row.qtd)} {bar}")
    peak = agg.sort_values("qtd", ascending=False).iloc[0]
    pm = peak["mes_ingresso"]
    plabel = pm.strftime("%Y-%m") if hasattr(pm, "strftime") else str(pm)[:7]
    lines.append("")
    lines.append(
        f"Pico em **{plabel}** com {_fmt_n(peak['qtd'])} ordens; "
        f"série cobre {len(agg)} meses."
    )
    return DataCard(
        "ce-reclamacoes-totais-evolucao",
        "CE — evolução mensal das reclamações totais",
        "\n".join(lines),
        region="CE",
    )


def _ce_total_grupo_card(groups: pd.DataFrame) -> DataCard:
    lines = ["**Distribuição por grupo tarifário em CE** (reclamações totais):", ""]
    for row in groups.itertuples(index=False):
        lines.append(
            f"- **{row.grupo}**: {_fmt_n(row.qtd_ordens)} "
            f"({_fmt_pct(row.percentual)})"
        )
    return DataCard(
        "ce-reclamacoes-totais-grupo",
        "CE — grupo tarifário (reclamações totais)",
        "\n".join(lines),
        region="CE",
    )


def _ce_total_causas_card(causas: pd.DataFrame) -> DataCard:
    labeled = causas[causas["causa_canonica"].astype(str) != "reclamacao_total_sem_causa"]
    if labeled.empty:
        return DataCard(
            "ce-reclamacoes-totais-causas",
            "CE — causas rotuladas (reclamações totais)",
            "Sem causas rotuladas no universo total.",
            region="CE",
        )
    total = int(labeled["qtd_ordens"].sum())
    top = labeled.iloc[0]
    header = (
        f"A principal causa-raiz rotulada em CE é **{top.causa_canonica}** com "
        f"**{_fmt_n(top.qtd_ordens)}** ordens ({_fmt_pct(top.qtd_ordens / total)})."
    )
    lines = [
        header,
        "",
        f"**Causas-raiz rotuladas entre as reclamações totais de CE** "
        f"(~{_fmt_n(total)} ordens com rótulo operacional):",
        "",
    ]
    for row in labeled.head(10).itertuples(index=False):
        lines.append(
            f"- **{row.causa_canonica}**: {_fmt_n(row.qtd_ordens)} "
            f"({_fmt_pct(row.qtd_ordens / total)})"
        )
    return DataCard(
        "ce-reclamacoes-totais-causas",
        "CE — causas rotuladas (reclamações totais)",
        "\n".join(lines),
        region="CE",
    )


def _data_quality_notes_card(frame: pd.DataFrame) -> DataCard:
    ce = _coverage_window(frame, "CE")
    sp = _coverage_window(frame, "SP")
    body = (
        "Caveats de qualidade de dados para uso analítico:\n\n"
        "- SP tem viés forte para ERRO_LEITURA e taxa de refaturamento resolvido zerada.\n"
        f"- Cobertura CE: {ce['start']} → {ce['end']} ({_fmt_n(ce['days'])} dias).\n"
        f"- Cobertura SP: {sp['start']} → {sp['end']} ({_fmt_n(sp['days'])} dias).\n"
        "- Interpretações comparativas devem explicitar esses vieses."
    )
    return DataCard(
        "data-quality-notes",
        "Notas de qualidade dos dados CE/SP",
        body,
        region="CE+SP",
    )


_SP_FILTERS: dict[str, list[str]] = {"regiao": ["SP"]}


def _ce_mvp_extra_cards(store: DataStore) -> list[DataCard]:
    """CE MVP: top instalações + mensal×assunto + mensal×causa."""
    top_inst = store.aggregate("top_instalacoes", _CE_TOTAL_FILTERS, include_total=True)
    month_assunto = store.aggregate(
        "monthly_assunto_breakdown", _CE_TOTAL_FILTERS, include_total=True
    )
    month_causa = store.aggregate(
        "monthly_causa_breakdown", _CE_TOTAL_FILTERS, include_total=True
    )
    return [
        _top_instalacoes_card(
            top_inst,
            anchor="ce-top-instalacoes",
            title="CE — instalações (UCs) com mais reclamações",
            region="CE",
            context_label="CE (reclamações totais, ~167,6k ordens)",
        ),
        _monthly_assunto_card(
            month_assunto,
            anchor="ce-reclamacoes-totais-mensal-assuntos",
            title="CE — assuntos principais por mês (reclamações totais)",
            region="CE",
            context_label="CE",
        ),
        _monthly_causa_card(
            month_causa,
            anchor="ce-reclamacoes-totais-mensal-causas",
            title="CE — causas-raiz principais por mês (reclamações totais rotuladas)",
            region="CE",
            context_label="CE",
        ),
    ]


def _sp_n1_cards(store: DataStore) -> list[DataCard]:
    """Paridade SP dentro do universo N1 (~12,1k tickets erro_leitura)."""
    overview = store.aggregate("overview", _SP_FILTERS)
    assuntos = store.aggregate("top_assuntos", _SP_FILTERS)
    causas = store.aggregate("top_causas", _SP_FILTERS)
    monthly = store.aggregate("monthly_volume", _SP_FILTERS)
    groups = store.aggregate("by_group", _SP_FILTERS)
    top_inst = store.aggregate("top_instalacoes", _SP_FILTERS)
    return [
        _sp_overview_card(overview),
        _sp_assuntos_card(assuntos),
        _sp_causas_card(causas),
        _sp_mensal_card(monthly),
        _sp_grupo_card(groups),
        _top_instalacoes_card(
            top_inst,
            anchor="sp-n1-top-instalacoes",
            title="SP — instalações (UCs) com mais tickets N1",
            region="SP",
            context_label="SP (N1 erro_leitura, ~12,1k tickets)",
        ),
    ]


def _sp_overview_card(overview: pd.DataFrame) -> DataCard:
    if overview.empty:
        return DataCard(
            "sp-n1-overview",
            "SP — visão geral (N1 erro_leitura)",
            "Sem dados disponíveis.",
            region="SP",
        )
    row = overview.iloc[0]
    body = (
        f"Em **SP**, o dataset N1 contém **{_fmt_n(row['total_registros'])} tickets** "
        f"(100% ERRO_LEITURA, cobertura 2025-07 → 2026-03). "
        f"Taxa de refaturamento resolvido é **{_fmt_pct(float(row['taxa_refaturamento']))}** "
        f"— viés conhecido (a origem não registra refaturamento em SP).\n\n"
        "Para análises comparativas, consulte também `data-quality-notes`."
    )
    return DataCard(
        "sp-n1-overview",
        "SP — visão geral (N1 erro_leitura)",
        body,
        region="SP",
    )


def _sp_assuntos_card(assuntos: pd.DataFrame) -> DataCard:
    if assuntos.empty:
        return DataCard(
            "sp-n1-assuntos",
            "SP — principais assuntos (N1)",
            "Sem dados de assunto disponíveis.",
            region="SP",
        )
    top = assuntos.iloc[0]
    header = (
        f"O principal assunto de reclamação em SP é **{top.assunto}** com "
        f"**{_fmt_n(top.qtd_ordens)}** tickets ({_fmt_pct(top.percentual)})."
    )
    lines = [header, "", "**Top assuntos em SP (N1)**:", ""]
    for row in assuntos.head(10).itertuples(index=False):
        lines.append(
            f"- **{row.assunto}**: {_fmt_n(row.qtd_ordens)} "
            f"({_fmt_pct(row.percentual)})"
        )
    return DataCard(
        "sp-n1-assuntos",
        "SP — principais assuntos (N1)",
        "\n".join(lines),
        region="SP",
    )


def _sp_causas_card(causas: pd.DataFrame) -> DataCard:
    if causas.empty:
        return DataCard(
            "sp-n1-causas",
            "SP — principais causas-raiz (N1)",
            "Sem causas rotuladas disponíveis.",
            region="SP",
        )
    top = causas.iloc[0]
    header = (
        f"A principal causa-raiz em SP é **{top.causa_canonica}** com "
        f"**{_fmt_n(top.qtd_ordens)}** tickets ({_fmt_pct(top.percentual)})."
    )
    lines = [header, "", "**Top causas em SP (N1)**:", ""]
    for row in causas.head(10).itertuples(index=False):
        lines.append(
            f"- **{row.causa_canonica}**: {_fmt_n(row.qtd_ordens)} "
            f"({_fmt_pct(row.percentual)})"
        )
    return DataCard(
        "sp-n1-causas",
        "SP — principais causas-raiz (N1)",
        "\n".join(lines),
        region="SP",
    )


def _sp_mensal_card(monthly: pd.DataFrame) -> DataCard:
    if monthly.empty:
        return DataCard(
            "sp-n1-mensal",
            "SP — evolução mensal (N1)",
            "Sem dados mensais disponíveis.",
            region="SP",
        )
    agg = monthly.groupby("mes_ingresso", as_index=False).agg(qtd=("qtd_erros", "sum"))
    agg = agg.sort_values("mes_ingresso")
    peak = agg.sort_values("qtd", ascending=False).iloc[0]
    pm = peak["mes_ingresso"]
    plabel = pm.strftime("%Y-%m") if hasattr(pm, "strftime") else str(pm)[:7]
    header = (
        f"Em SP, o volume mensal tem pico em **{plabel}** "
        f"com {_fmt_n(peak['qtd'])} tickets; a série cobre {len(agg)} meses."
    )
    lines = [header, "", "**Evolução mensal SP (N1)**:", ""]
    max_val = int(agg["qtd"].max()) or 1
    for row in agg.itertuples(index=False):
        m = row.mes_ingresso
        label = m.strftime("%Y-%m") if hasattr(m, "strftime") else str(m)[:7]
        bar = "#" * max(1, int(int(row.qtd) / max_val * 18))
        lines.append(f"- `{label}`: {_fmt_n(row.qtd)} {bar}")
    return DataCard(
        "sp-n1-mensal",
        "SP — evolução mensal (N1)",
        "\n".join(lines),
        region="SP",
    )


def _sp_grupo_card(groups: pd.DataFrame) -> DataCard:
    if groups.empty:
        return DataCard(
            "sp-n1-grupo",
            "SP — grupo tarifário (N1)",
            "Sem dados de grupo disponíveis.",
            region="SP",
        )
    top = groups.iloc[0]
    header = (
        f"Em SP, o grupo tarifário dominante é **{top.grupo}** com "
        f"**{_fmt_n(top.qtd_ordens)}** tickets ({_fmt_pct(top.percentual)})."
    )
    lines = [header, "", "**Distribuição por grupo em SP (N1)**:", ""]
    for row in groups.itertuples(index=False):
        lines.append(
            f"- **{row.grupo}**: {_fmt_n(row.qtd_ordens)} ({_fmt_pct(row.percentual)})"
        )
    return DataCard(
        "sp-n1-grupo",
        "SP — grupo tarifário (N1)",
        "\n".join(lines),
        region="SP",
    )


def _sp_causa_observacoes_card(data: pd.DataFrame) -> DataCard:
    if data.empty:
        return DataCard(
            "sp-causa-observacoes",
            "SP — causa-raiz evidenciada nas observações",
            "Sem evidência textual disponível para inferência de causa em SP.",
            region="SP",
        )
    row = data.iloc[0]
    body = (
        f"Em SP, a causa-raiz mais evidenciada nas observações é **{row['causa_lider']}** "
        f"com {_fmt_n(row['qtd_ordens'])} ordens ({_fmt_pct(float(row['percentual']))}).\n\n"
        f"Assunto associado mais frequente: **{row['assunto_top']}**.\n"
        f"Exemplos de observação: {row['observacoes_exemplo'] or '(não disponível)'}"
    )
    return DataCard(
        "sp-causa-observacoes",
        "SP — causa-raiz evidenciada nas observações",
        body,
        region="SP",
    )


def _sp_perfil_assunto_lider_card(data: pd.DataFrame) -> DataCard:
    if data.empty:
        return DataCard(
            "sp-perfil-assunto-lider",
            "SP — perfil do assunto mais reclamado",
            "Sem dados suficientes para perfil detalhado do assunto líder em SP.",
            region="SP",
        )
    row = data.iloc[0]
    body = (
        f"No assunto líder de SP (**{row['assunto_lider']}**, {_fmt_n(row['qtd_ordens'])} ordens), "
        "o perfil agregado indica: mês de fatura mais reclamado "
        f"**{row['fat_reclamada_top'] or 'n/d'}**, "
        "tempo médio emissão→reclamação "
        f"**{float(row['dias_emissao_ate_reclamacao_medio']):.1f} dias**, "
        f"tipo de medidor predominante **{row['tipo_medidor_dominante'] or 'n/d'}**, "
        "valor médio da fatura reclamada "
        f"**R$ {float(row['valor_fatura_reclamada_medio']):.2f}**.\n\n"
        f"Cobertura do perfil: fatura {100.0 * float(row['cobertura_fatura_pct']):.1f}% "
        f"| medidor {100.0 * float(row['cobertura_medidor_pct']):.1f}%."
    )
    return DataCard(
        "sp-perfil-assunto-lider",
        "SP — perfil do assunto mais reclamado",
        body,
        region="SP",
    )


def _sp_tipos_medidor_card(data: pd.DataFrame) -> DataCard:
    if data.empty:
        return DataCard(
            "sp-tipos-medidor",
            "SP — tipos de medidor mais recorrentes",
            "Sem dados de tipo de medidor disponíveis para SP.",
            region="SP",
        )
    top = data.iloc[0]
    header = (
        f"Em SP, o tipo de medidor mais recorrente nas reclamações é "
        f"**{top['tipo_medidor_dominante']}** com {_fmt_n(top['qtd_ordens'])} ordens "
        f"({_fmt_pct(float(top['percentual']))})."
    )
    lines = [header, "", "**Top tipos de medidor em SP**:", ""]
    for row in data.itertuples(index=False):
        lines.append(
            f"- **{row.tipo_medidor_dominante}**: {_fmt_n(row.qtd_ordens)} ordens "
            f"({_fmt_pct(float(row.percentual))}), {_fmt_n(row.qtd_instalacoes)} instalações"
        )
    return DataCard(
        "sp-tipos-medidor",
        "SP — tipos de medidor mais recorrentes",
        "\n".join(lines),
        region="SP",
    )


def _sp_tipos_medidor_digitacao_card(data: pd.DataFrame) -> DataCard:
    if data.empty:
        return DataCard(
            "sp-tipos-medidor-digitacao",
            "SP — tipos de medidor em reclamações de digitação",
            "Sem dados de tipo de medidor para ocorrências de digitação em SP.",
            region="SP",
        )
    top = data.iloc[0]
    header = (
        "Nas reclamações de digitação em SP, o tipo de medidor mais recorrente é "
        f"**{top['tipo_medidor_dominante']}** com {_fmt_n(top['qtd_ordens'])} ordens "
        f"({_fmt_pct(float(top['percentual']))})."
    )
    lines = [header, "", "**Top tipos de medidor em casos de digitação (SP)**:", ""]
    for row in data.itertuples(index=False):
        lines.append(
            f"- **{row.tipo_medidor_dominante}**: {_fmt_n(row.qtd_ordens)} ordens "
            f"({_fmt_pct(float(row.percentual))}), {_fmt_n(row.qtd_instalacoes)} instalações"
        )
    return DataCard(
        "sp-tipos-medidor-digitacao",
        "SP — tipos de medidor em reclamações de digitação",
        "\n".join(lines),
        region="SP",
    )


def _sp_causas_por_tipo_medidor_card(data: pd.DataFrame) -> DataCard:
    if data.empty:
        return DataCard(
            "sp-causas-por-tipo-medidor",
            "SP — top motivos por tipo de medidor",
            "Sem dados suficientes para causas por tipo de medidor em SP.",
            region="SP",
        )
    ordered = data.sort_values(
        ["qtd_total_tipo", "rank"],
        ascending=[False, True],
    ).reset_index(drop=True)
    first = ordered.iloc[0]
    header = (
        f"Em SP, para o medidor **{first['tipo_medidor_dominante']}**, "
        f"a causa principal é **{first['causa_canonica']}** com "
        f"{_fmt_n(first['qtd_ordens'])} ordens "
        f"({_fmt_pct(float(first['percentual_no_tipo']))} dentro do tipo)."
    )
    lines = [header, "", "**Top 5 causas por tipo de medidor (SP)**:", ""]
    for meter, group in ordered.groupby("tipo_medidor_dominante", sort=False):
        group = group.sort_values("rank").head(5)
        total = int(group.iloc[0]["qtd_total_tipo"])
        rendered = "; ".join(
            (
                f"{int(row.rank)}. {row.causa_canonica} "
                f"({_fmt_n(row.qtd_ordens)}, {_fmt_pct(float(row.percentual_no_tipo))})"
            )
            for row in group.itertuples(index=False)
        )
        lines.append(f"- **{meter}** ({_fmt_n(total)} ordens): {rendered}")
    return DataCard(
        "sp-causas-por-tipo-medidor",
        "SP — top motivos por tipo de medidor",
        "\n".join(lines),
        region="SP",
    )


def _motivos_taxonomia_card(data: pd.DataFrame, *, region: str) -> DataCard:
    if data.empty:
        return DataCard(
            "motivos-taxonomia-ce-sp",
            "Taxonomia consolidada de motivos (assunto + causa)",
            "Sem dados para consolidar taxonomia de motivos em CE/SP.",
            region=region,
        )
    lines = [
        "Taxonomia consolidada de motivos de reclamação (assunto + causa canônica):",
        "",
        "**Top combinações CE/SP**:",
        "",
    ]
    for row in data.head(20).itertuples(index=False):
        lines.append(
            f"- [{row.regiao}] **{row.assunto}** + {row.causa_canonica}: "
            f"{_fmt_n(row.qtd_ordens)} ({_fmt_pct(float(row.percentual))})"
        )
    return DataCard(
        "motivos-taxonomia-ce-sp",
        "Taxonomia consolidada de motivos (assunto + causa)",
        "\n".join(lines),
        region=region,
    )


def _top_instalacoes_card(
    top_inst: pd.DataFrame,
    *,
    anchor: str,
    title: str,
    region: str,
    context_label: str,
) -> DataCard:
    if top_inst.empty:
        return DataCard(
            anchor,
            title,
            "Sem dados de instalação disponíveis.",
            region=region,
        )
    top = top_inst.iloc[0]
    inst_id = str(top.instalacao)
    assunto_top = str(top.assunto_top) if top.assunto_top else "(não informado)"
    header = (
        f"A instalação (UC) com mais reclamações em {context_label} é "
        f"**{inst_id}** com **{_fmt_n(top.qtd_ordens)} ordens** "
        f"(assunto dominante: {assunto_top}, taxa refatur "
        f"{_fmt_pct(float(top.taxa_refaturamento))})."
    )
    lines = [
        header,
        "",
        "**Top 20 instalações por volume** (ID técnico anonimizado):",
        "",
    ]
    for row in top_inst.head(20).itertuples(index=False):
        assunto = str(row.assunto_top) if row.assunto_top else "(n/d)"
        meter = (
            f", medidor {row.tipo_medidor_dominante}"
            if hasattr(row, "tipo_medidor_dominante") and row.tipo_medidor_dominante
            else ""
        )
        lines.append(
            f"- `{row.instalacao}`: {_fmt_n(row.qtd_ordens)} ordens — "
            f"{assunto}{meter} (refatur {_fmt_pct(float(row.taxa_refaturamento))})"
        )
    return DataCard(anchor, title, "\n".join(lines), region=region)


def _monthly_assunto_card(
    breakdown: pd.DataFrame,
    *,
    anchor: str,
    title: str,
    region: str,
    context_label: str,
) -> DataCard:
    if breakdown.empty:
        return DataCard(
            anchor,
            title,
            "Sem dados mensais disponíveis.",
            region=region,
        )
    by_month: dict[str, list[tuple[str, int]]] = {}
    for row in breakdown.itertuples(index=False):
        m = row.mes_ingresso
        label = m.strftime("%Y-%m") if hasattr(m, "strftime") else str(m)[:7]
        by_month.setdefault(label, []).append((str(row.assunto), int(row.qtd_ordens)))
    last_label = sorted(by_month)[-1]
    first = by_month[last_label][0]
    header = (
        f"Em {context_label}, no mês mais recente (**{last_label}**) o principal "
        f"assunto foi **{first[0]}** com {_fmt_n(first[1])} ordens."
    )
    lines = [header, "", f"**Top-3 assuntos por mês em {context_label}**:", ""]
    for label in sorted(by_month):
        items = by_month[label]
        rendered = "; ".join(f"{a} ({_fmt_n(q)})" for a, q in items[:3])
        lines.append(f"- `{label}`: {rendered}")
    return DataCard(anchor, title, "\n".join(lines), region=region)


def _monthly_causa_card(
    breakdown: pd.DataFrame,
    *,
    anchor: str,
    title: str,
    region: str,
    context_label: str,
) -> DataCard:
    if breakdown.empty:
        return DataCard(
            anchor,
            title,
            "Sem dados mensais de causa-raiz rotulada.",
            region=region,
        )
    by_month: dict[str, list[tuple[str, int]]] = {}
    for row in breakdown.itertuples(index=False):
        m = row.mes_ingresso
        label = m.strftime("%Y-%m") if hasattr(m, "strftime") else str(m)[:7]
        by_month.setdefault(label, []).append(
            (str(row.causa_canonica), int(row.qtd_ordens))
        )
    last_label = sorted(by_month)[-1]
    first = by_month[last_label][0]
    header = (
        f"Em {context_label}, no mês mais recente (**{last_label}**) a principal "
        f"causa-raiz rotulada foi **{first[0]}** com {_fmt_n(first[1])} ordens."
    )
    lines = [
        header,
        "",
        f"**Top-3 causas-raiz rotuladas por mês em {context_label}**:",
        "",
    ]
    for label in sorted(by_month):
        items = by_month[label]
        rendered = "; ".join(f"{c} ({_fmt_n(q)})" for c, q in items[:3])
        lines.append(f"- `{label}`: {rendered}")
    return DataCard(anchor, title, "\n".join(lines), region=region)


def _coverage_window(frame: pd.DataFrame, region: str) -> dict[str, str | int]:
    if frame.empty or "regiao" not in frame.columns or "data_ingresso" not in frame.columns:
        return {"start": "n/d", "end": "n/d", "days": 0}
    data = frame.loc[frame["regiao"].astype(str) == region, "data_ingresso"].dropna()
    if data.empty:
        return {"start": "n/d", "end": "n/d", "days": 0}
    start = data.min()
    end = data.max()
    days = int((end - start).days + 1)
    return {
        "start": start.strftime("%Y-%m-%d"),
        "end": end.strftime("%Y-%m-%d"),
        "days": max(days, 0),
    }
