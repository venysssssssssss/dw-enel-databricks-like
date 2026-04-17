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
