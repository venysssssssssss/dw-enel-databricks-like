"""Unit tests for the sp_severidade_* family registered in the data plane."""

from __future__ import annotations

import pandas as pd
import pytest

from src.data_plane.views import VIEW_REGISTRY, get_view
from src.viz.erro_leitura_dashboard_data import (
    _attach_severidade,
    _filter_sp_severidade,
    sp_severidade_categorias,
    sp_severidade_causas,
    sp_severidade_mensal,
    sp_severidade_overview,
    sp_severidade_ranking,
)


def _row(**overrides) -> dict:
    base = {
        "ordem": "ord-1",
        "regiao": "SP",
        "causa_canonica": "digitacao",
        "instalacao": "INS-1",
        "instalacao_hash": "h1",
        "flag_resolvido_com_refaturamento": False,
        "has_causa_raiz_label": True,
        "mes_ingresso": pd.Timestamp("2026-01-01"),
        "data_ingresso": pd.Timestamp("2026-01-15"),
        "valor_fatura_reclamada_medio": 500.0,
    }
    base.update(overrides)
    return base


def _frame(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(rows)


# -------------------------- helpers --------------------------


def test_attach_severidade_fills_defaults_for_unknown_cause() -> None:
    df = _frame([_row(causa_canonica="completely-unknown-cause")])
    out = _attach_severidade(df)
    assert out.loc[0, "severidade"] == "low"
    assert out.loc[0, "categoria"] == "nao_classificada"
    assert out.loc[0, "peso_severidade"] == pytest.approx(1.0)


def test_filter_sp_severidade_drops_ce_rows() -> None:
    df = _frame(
        [
            _row(ordem="a", regiao="SP", causa_canonica="autoleitura_cliente"),
            _row(ordem="b", regiao="CE", causa_canonica="autoleitura_cliente"),
        ]
    )
    out = _filter_sp_severidade(df, "high")
    assert set(out["regiao"]) == {"SP"}


def test_filter_sp_severidade_accepts_pt_aliases() -> None:
    df = _frame([_row(causa_canonica="autoleitura_cliente")])
    via_alias = _filter_sp_severidade(df, "alta")
    via_canonical = _filter_sp_severidade(df, "high")
    assert len(via_alias) == len(via_canonical)


# -------------------------- overview --------------------------


def test_overview_empty_frame_returns_zeroed_row() -> None:
    out = sp_severidade_overview(pd.DataFrame(), severidade="high")
    assert len(out) == 1
    assert int(out.iloc[0]["total"]) == 0
    assert int(out.iloc[0]["procedentes"]) == 0


def test_overview_counts_unique_orders_and_categorias() -> None:
    df = _frame(
        [
            _row(ordem="a", causa_canonica="autoleitura_cliente"),
            _row(ordem="b", causa_canonica="autoleitura_cliente"),
            _row(ordem="c", causa_canonica="impedimento_acesso"),
        ]
    )
    out = sp_severidade_overview(df, severidade="high").iloc[0]
    assert int(out["total"]) == 3
    assert int(out["categorias_count"]) >= 1
    assert 0.0 <= float(out["top3_share"]) <= 1.0


# -------------------------- mensal --------------------------


def test_mensal_returns_monotonic_iso_dates() -> None:
    df = _frame(
        [
            _row(ordem="a", mes_ingresso=pd.Timestamp("2026-01-01")),
            _row(ordem="b", mes_ingresso=pd.Timestamp("2026-02-01")),
            _row(ordem="c", mes_ingresso=pd.Timestamp("2026-02-01")),
        ]
    )
    out = sp_severidade_mensal(df, severidade="high")
    assert list(out.columns) == ["mes_ingresso", "qtd_erros", "procedentes", "improcedentes"]
    assert list(out["mes_ingresso"]) == sorted(out["mes_ingresso"])
    assert int(out.iloc[-1]["qtd_erros"]) == 2


# -------------------------- categorias --------------------------


def test_categorias_orders_desc_and_collapses_tail() -> None:
    rows = []
    for i in range(20):
        rows.append(_row(ordem=f"o{i}", causa_canonica="autoleitura_cliente"))
    rows.append(_row(ordem="z", causa_canonica="impedimento_acesso"))
    out = sp_severidade_categorias(_frame(rows), severidade="high", limit=1)
    assert out.iloc[0]["categoria"] != ""
    assert "outros" in out["categoria_id"].tolist() or len(out) == 1


# -------------------------- causas --------------------------


def test_causas_returns_scatter_payload_columns() -> None:
    df = _frame(
        [
            _row(ordem="a", causa_canonica="autoleitura_cliente"),
            _row(
                ordem="b",
                causa_canonica="autoleitura_cliente",
                flag_resolvido_com_refaturamento=True,
            ),
            _row(ordem="c", causa_canonica="impedimento_acesso"),
        ]
    )
    out = sp_severidade_causas(df, severidade="high")
    expected = {"id", "nome", "vol", "proc", "reinc", "cat"}
    assert expected.issubset(out.columns)
    assert (out["proc"] >= 0).all() and (out["proc"] <= 100).all()


# -------------------------- ranking --------------------------


def test_ranking_only_returns_repeating_installations() -> None:
    df = _frame(
        [
            _row(ordem="a", instalacao="INS-A", instalacao_hash="ha"),
            _row(ordem="b", instalacao="INS-A", instalacao_hash="ha"),
            _row(ordem="c", instalacao="INS-B", instalacao_hash="hb"),
        ]
    )
    out = sp_severidade_ranking(df, severidade="high", limit=5)
    assert all(int(v) > 1 for v in out["reinc"])
    assert "INS-A" in out["inst"].tolist()
    assert all(len(spark) == 9 for spark in out["spark"])


def test_ranking_handles_no_repetitions() -> None:
    df = _frame([_row(ordem="a", instalacao_hash="solo")])
    out = sp_severidade_ranking(df, severidade="high")
    assert out.empty


# -------------------------- registry --------------------------


def test_registry_exposes_ten_sp_severidade_views() -> None:
    expected = {
        "sp_severidade_alta_overview",
        "sp_severidade_critica_overview",
        "sp_severidade_alta_mensal",
        "sp_severidade_critica_mensal",
        "sp_severidade_alta_categorias",
        "sp_severidade_critica_categorias",
        "sp_severidade_alta_causas",
        "sp_severidade_critica_causas",
        "sp_severidade_alta_ranking",
        "sp_severidade_critica_ranking",
    }
    assert expected.issubset(set(VIEW_REGISTRY.keys()))


@pytest.mark.parametrize(
    "view_id,sev",
    [
        ("sp_severidade_alta_overview", "high"),
        ("sp_severidade_critica_overview", "critical"),
        ("sp_severidade_alta_mensal", "high"),
        ("sp_severidade_critica_ranking", "critical"),
    ],
)
def test_registry_kwargs_carry_correct_severity(view_id: str, sev: str) -> None:
    spec = get_view(view_id)
    assert spec.kwargs.get("severidade") == sev
