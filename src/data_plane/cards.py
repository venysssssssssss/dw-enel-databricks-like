"""RAG data cards generated from the same data plane views used by BI."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import TYPE_CHECKING

from src.rag.ingestion import Chunk, _approx_tokens

if TYPE_CHECKING:
    import pandas as pd

    from src.data_plane.store import DataStore


@dataclass(frozen=True, slots=True)
class DataCard:
    anchor: str
    title: str
    body: str


def build_data_cards(store: DataStore) -> list[Chunk]:
    version = store.version()
    if not version.sources:
        return []
    cards = [
        _overview_card(store.aggregate("overview")),
        *_by_region_cards(store.aggregate("by_region"), total=_total(store.aggregate("overview"))),
        _top_assunto_card(store.aggregate("top_assuntos")),
        _top_causa_card(store.aggregate("top_causas")),
        _refaturamento_card(
            store.aggregate("refaturamento_summary"),
            store.aggregate("by_region"),
            store.aggregate("top_assuntos"),
        ),
        _monthly_card(store.aggregate("monthly_volume")),
        _grupo_card(store.aggregate("by_group")),
    ]
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
    )


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


def _overview_card(overview: pd.DataFrame) -> DataCard:
    if overview.empty:
        return DataCard(
            "visao-geral",
            "Visão geral das reclamações CE + SP",
            "Sem dados disponíveis.",
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
    return DataCard("visao-geral", "Visão geral das reclamações CE + SP", body)


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


def _top_assunto_card(top: pd.DataFrame) -> DataCard:
    lines = ["Os **assuntos mais frequentes** no dataset analítico atual:", ""]
    for row in top.itertuples(index=False):
        lines.append(
            f"- **{row.assunto}**: {_fmt_n(row.qtd_ordens)} "
            f"ordens ({_fmt_pct(row.percentual)})"
        )
    return DataCard("top-assuntos", "Top assuntos de reclamação", "\n".join(lines))


def _top_causa_card(top: pd.DataFrame) -> DataCard:
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
    )


def _refaturamento_card(
    summary: pd.DataFrame,
    by_region: pd.DataFrame,
    top_assuntos: pd.DataFrame,
) -> DataCard:
    if summary.empty:
        return DataCard(
            "refaturamento",
            "Impacto de refaturamento como desfecho",
            "Sem dados disponíveis.",
        )
    row = summary.iloc[0]
    lines = [
        f"**Refaturamento** foi o desfecho em {_fmt_n(row['refaturadas'])} "
        f"({_fmt_pct(float(row['taxa_refaturamento']))}) das {_fmt_n(row['total'])} ordens totais.",
        "",
        "**Distribuição por região**:",
    ]
    for region in by_region.itertuples(index=False):
        lines.append(
            f"- {region.regiao}: {_fmt_n(region.ordens_refaturadas)} "
            "ordens resolvidas com refaturamento"
        )
    lines.append("")
    lines.append("**Assuntos mais relevantes para investigação**:")
    for assunto in top_assuntos.head(6).itertuples(index=False):
        lines.append(f"- {assunto.assunto}: {_fmt_n(assunto.qtd_ordens)}")
    return DataCard("refaturamento", "Impacto de refaturamento como desfecho", "\n".join(lines))


def _monthly_card(monthly: pd.DataFrame) -> DataCard:
    if monthly.empty:
        return DataCard(
            "evolucao-mensal",
            "Evolução mensal de reclamações",
            "(sem dados de data disponíveis)",
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
    return DataCard("evolucao-mensal", "Evolução mensal de reclamações", "\n".join(lines))


def _grupo_card(groups: pd.DataFrame) -> DataCard:
    lines = ["Distribuição por **grupo tarifário** no dataset analítico atual:", ""]
    for row in groups.itertuples(index=False):
        lines.append(f"- **{row.grupo}**: {_fmt_n(row.qtd_ordens)} ({_fmt_pct(row.percentual)})")
    return DataCard("grupo-tarifario", "Distribuição por grupo tarifário", "\n".join(lines))
