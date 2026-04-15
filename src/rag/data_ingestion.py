"""Ingestão de dados reais CE/SP no corpus RAG.

Em vez de indexar linhas individuais (volume + PII), geramos **data cards**:
resumos textuais agregados por região/mês/assunto/causa-raiz a partir do
silver `erro_leitura_normalizado.csv`. Cada card é um chunk Markdown que o
retriever pode trazer como contexto para perguntas de análise.

Decisões:
- Fonte única: `data/silver/erro_leitura_normalizado.csv` (já normalizado,
  PII tratado no silver, inclui flag_resolvido_com_refaturamento e causa_raiz).
- Cards por: (1) visão geral, (2) por região CE/SP, (3) top assuntos,
  (4) top causas-raiz, (5) refaturamento, (6) evolução mensal, (7) por grupo.
- Todos os cards carregam `doc_type="data"` e `source_path="data/silver/..."`.
- Determinístico: mesmo CSV → mesmos ids (SHA256 do conteúdo).
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from src.rag.ingestion import Chunk, _approx_tokens


_SILVER_PATH = Path("data/silver/erro_leitura_normalizado.csv")
_USECOLS = [
    "grupo",
    "assunto",
    "_source_region",
    "causa_raiz",
    "flag_resolvido_com_refaturamento",
    "dt_ingresso",
]


@dataclass(frozen=True, slots=True)
class DataCard:
    anchor: str
    title: str
    body: str


def _chunk_from_card(card: DataCard, source_path: str) -> Chunk:
    text = f"# {card.title}\n\n{card.body}".strip()
    chunk_key = f"{source_path}::{card.anchor}::{text[:120]}"
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
    )


def _fmt_pct(part: float, total: float) -> str:
    if total == 0:
        return "0.0%"
    return f"{100.0 * part / total:.1f}%"


def _fmt_n(value: int | float) -> str:
    """Formata inteiro com separador de milhar pt-BR: 184690 -> '184.690'."""
    return f"{int(value):,}".replace(",", ".")


def _overview_card(df) -> DataCard:
    total = len(df)
    ce = int((df["_source_region"] == "CE").sum())
    sp = int((df["_source_region"] == "SP").sum())
    refat = int(df["flag_resolvido_com_refaturamento"].fillna(False).astype(bool).sum())
    com_causa = int(df["causa_raiz"].notna().sum())
    body = (
        f"Base de reclamações ENEL consolidada com **{_fmt_n(total)} ordens** reais, "
        f"cobrindo duas regiões: **Ceará (CE) com {_fmt_n(ce)} registros "
        f"({_fmt_pct(ce, total)})** e **São Paulo (SP) com {_fmt_n(sp)} registros "
        f"({_fmt_pct(sp, total)})**. Das ordens analisadas, "
        f"**{_fmt_n(refat)} ({_fmt_pct(refat, total)})** foram resolvidas via "
        f"refaturamento e **{_fmt_n(com_causa)} ({_fmt_pct(com_causa, total)})** "
        "possuem causa-raiz rotulada manualmente pela operação. "
        "A cobertura temporal vai de janeiro/2025 a março/2026."
    )
    return DataCard(anchor="visao-geral", title="Visão geral das reclamações CE + SP", body=body)


def _by_region_cards(df) -> list[DataCard]:
    cards: list[DataCard] = []
    for region in ("CE", "SP"):
        sub = df[df["_source_region"] == region]
        if sub.empty:
            continue
        total = len(sub)
        top_ass = sub["assunto"].value_counts().head(5)
        top_causa = sub["causa_raiz"].value_counts().head(5)
        refat_pct = _fmt_pct(
            int(sub["flag_resolvido_com_refaturamento"].fillna(False).astype(bool).sum()),
            total,
        )
        lines = [
            f"Região **{region}** concentra **{_fmt_n(total)} ordens** reais "
            f"({_fmt_pct(total, len(df))} do total da base). Refaturamento "
            f"resolve {refat_pct} dos casos.",
            "",
            "**Top 5 assuntos**:",
        ]
        for name, count in top_ass.items():
            pct = _fmt_pct(int(count), total)
            lines.append(f"- {name}: {_fmt_n(count)} ({pct})")
        lines.append("")
        lines.append("**Top 5 causas-raiz rotuladas**:")
        for name, count in top_causa.items():
            pct = _fmt_pct(int(count), total)
            label = str(name)[:120]
            lines.append(f"- {label}: {_fmt_n(count)} ({pct})")
        cards.append(
            DataCard(
                anchor=f"regiao-{region.lower()}",
                title=f"Reclamações na região {region}",
                body="\n".join(lines),
            )
        )
    return cards


def _top_assunto_card(df) -> DataCard:
    total = len(df)
    top = df["assunto"].value_counts().head(12)
    lines = [
        f"Os **12 assuntos mais frequentes** em {_fmt_n(total)} reclamações "
        "CE+SP analisadas:",
        "",
    ]
    for name, count in top.items():
        pct = _fmt_pct(int(count), total)
        lines.append(f"- **{name}**: {_fmt_n(count)} ordens ({pct})")
    lines.append("")
    lines.append(
        "Refaturamento (produtos, grupo B, RPA, multa revelia, preventivo) "
        "domina o volume, seguido por erro de leitura e variação de consumo."
    )
    return DataCard(
        anchor="top-assuntos",
        title="Top assuntos de reclamação (CE + SP)",
        body="\n".join(lines),
    )


def _top_causa_card(df) -> DataCard:
    sub = df[df["causa_raiz"].notna()]
    total = len(sub)
    top = sub["causa_raiz"].value_counts().head(12)
    lines = [
        f"Entre as **{_fmt_n(total)} ordens rotuladas** com causa-raiz, as "
        "12 causas mais prevalentes:",
        "",
    ]
    for name, count in top.items():
        pct = _fmt_pct(int(count), total)
        label = str(name).strip()[:200]
        lines.append(f"- **{label}**: {_fmt_n(count)} ({pct})")
    lines.append("")
    lines.append(
        "Cobrança de multa de autoreligação, erro de leitura por digitação, "
        "compensação GD incorreta e faturamento por média concentram a maior "
        "parte das causas investigadas."
    )
    return DataCard(
        anchor="top-causas-raiz",
        title="Top causas-raiz identificadas pela operação",
        body="\n".join(lines),
    )


def _refaturamento_card(df) -> DataCard:
    flag = df["flag_resolvido_com_refaturamento"].fillna(False).astype(bool)
    total = len(df)
    refat = int(flag.sum())
    refat_ce = int(flag[df["_source_region"] == "CE"].sum())
    refat_sp = int(flag[df["_source_region"] == "SP"].sum())
    por_ass = df.loc[flag, "assunto"].value_counts().head(6)
    lines = [
        f"**Refaturamento** foi o desfecho em {_fmt_n(refat)} "
        f"({_fmt_pct(refat, total)}) das {_fmt_n(total)} ordens totais.",
        f"- CE: {_fmt_n(refat_ce)} ordens resolvidas com refaturamento",
        f"- SP: {_fmt_n(refat_sp)} ordens resolvidas com refaturamento",
        "",
        "**Assuntos mais associados a refaturamento**:",
    ]
    for name, count in por_ass.items():
        lines.append(f"- {name}: {_fmt_n(count)}")
    lines.append("")
    lines.append(
        "A flag `flag_resolvido_com_refaturamento` é derivada no silver a partir "
        "da devolutiva da ordem. Serve como proxy de impacto financeiro."
    )
    return DataCard(
        anchor="refaturamento",
        title="Impacto de refaturamento como desfecho",
        body="\n".join(lines),
    )


def _monthly_card(df) -> DataCard:
    import pandas as pd

    dt = pd.to_datetime(df["dt_ingresso"], errors="coerce")
    df2 = df.assign(mes=dt.dt.strftime("%Y-%m")).dropna(subset=["mes"])
    serie = df2["mes"].value_counts().sort_index()
    if serie.empty:
        return DataCard(
            anchor="evolucao-mensal",
            title="Evolução mensal de reclamações",
            body="(sem dados de data disponíveis)",
        )
    max_val = int(serie.max())
    lines = [
        "**Evolução mensal** do volume de reclamações (CE + SP):",
        "",
    ]
    for mes, count in serie.items():
        bar = "█" * max(1, int(count / max_val * 20))
        lines.append(f"- `{mes}`: {_fmt_n(count)} {bar}")
    peak_mes = serie.idxmax()
    lines.append("")
    lines.append(
        f"Pico em **{peak_mes}** com {_fmt_n(max_val)} ordens. Tendência geral "
        "é estável com oscilação típica de sazonalidade de faturamento."
    )
    return DataCard(
        anchor="evolucao-mensal",
        title="Evolução mensal de reclamações",
        body="\n".join(lines),
    )


def _grupo_card(df) -> DataCard:
    total = len(df)
    serie = df["grupo"].fillna("(não informado)").value_counts().head(6)
    lines = [
        f"Distribuição por **grupo tarifário** em {_fmt_n(total)} ordens (CE+SP):",
        "",
    ]
    for name, count in serie.items():
        pct = _fmt_pct(int(count), total)
        lines.append(f"- **{name}**: {_fmt_n(count)} ({pct})")
    lines.append("")
    lines.append(
        "GB (baixa tensão residencial/comercial) domina; GA concentra clientes "
        "de alta tensão; GERADORA/RECEPTORA são códigos de geração distribuída."
    )
    return DataCard(
        anchor="grupo-tarifario",
        title="Distribuição por grupo tarifário",
        body="\n".join(lines),
    )


def build_data_cards(silver_path: Path | None = None) -> list[Chunk]:
    """Lê o silver e devolve lista de Chunks prontos para indexar no RAG.

    Retorna lista vazia se pandas não disponível ou CSV inexistente.
    """
    try:
        import pandas as pd  # noqa: F401
    except ImportError:  # pragma: no cover
        return []

    path = silver_path or _SILVER_PATH
    if not path.exists():
        return []

    import pandas as pd

    df = pd.read_csv(path, usecols=_USECOLS, low_memory=False)
    source = f"{path.as_posix()}"

    cards: list[DataCard] = [
        _overview_card(df),
        *_by_region_cards(df),
        _top_assunto_card(df),
        _top_causa_card(df),
        _refaturamento_card(df),
        _monthly_card(df),
        _grupo_card(df),
    ]
    return [_chunk_from_card(c, source_path=source) for c in cards]
