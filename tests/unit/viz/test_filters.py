from __future__ import annotations

from datetime import date

import pandas as pd

from apps.streamlit.components.filters import (
    PRESET_CE,
    PRESET_LAST_30,
    PRESET_REFAT,
    DashboardFilters,
    active_filter_chips,
    apply_dashboard_filters,
    chips_markdown,
    default_filters,
    filter_options,
    filters_from_query_params,
    filters_to_query_params,
    normalize_filters,
    preset_filters,
)


def _frame() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "ordem": "1",
                "regiao": "CE",
                "causa_canonica": "digitacao",
                "topic_name": "topico_a",
                "data_ingresso": pd.Timestamp("2026-01-01"),
                "flag_resolvido_com_refaturamento": True,
            },
            {
                "ordem": "2",
                "regiao": "SP",
                "causa_canonica": "impedimento_acesso",
                "topic_name": "topico_b",
                "data_ingresso": pd.Timestamp("2026-02-15"),
                "flag_resolvido_com_refaturamento": False,
            },
            {
                "ordem": "3",
                "regiao": "CE",
                "causa_canonica": "indefinido",
                "topic_name": "topico_b",
                "data_ingresso": pd.Timestamp("2026-02-20"),
                "flag_resolvido_com_refaturamento": False,
            },
        ]
    )


def test_filter_options_and_default_filters_cover_frame() -> None:
    options = filter_options(_frame())
    filters = default_filters(options, include_total=True)

    assert options.regions == ("CE", "SP")
    assert options.min_date == date(2026, 1, 1)
    assert options.max_date == date(2026, 2, 20)
    assert filters.include_total is True
    assert filters.regions == options.regions


def test_normalize_filters_discards_invalid_values_and_swaps_dates() -> None:
    options = filter_options(_frame())
    filters = normalize_filters(
        DashboardFilters(
            regions=("RJ",),
            causes=("digitacao", "x"),
            topics=("topico_a",),
            start_date=date(2026, 3, 1),
            end_date=date(2026, 1, 1),
            theme="invalid",
        ),
        options,
    )

    assert filters.regions == options.regions
    assert filters.causes == ("digitacao",)
    assert filters.start_date == date(2026, 1, 1)
    assert filters.end_date == date(2026, 2, 20)
    assert filters.theme == "light"


def test_apply_dashboard_filters_combines_all_predicates() -> None:
    filtered = apply_dashboard_filters(
        _frame(),
        DashboardFilters(
            regions=("CE",),
            causes=("digitacao", "indefinido"),
            topics=("topico_a", "topico_b"),
            start_date=date(2026, 1, 1),
            end_date=date(2026, 2, 1),
            only_refaturamento=True,
        ),
    )

    assert filtered["ordem"].tolist() == ["1"]


def test_apply_dashboard_filters_handles_empty_frames() -> None:
    empty = _frame().iloc[0:0]

    assert apply_dashboard_filters(empty, DashboardFilters()).empty


def test_query_params_roundtrip() -> None:
    options = filter_options(_frame())
    filters = DashboardFilters(
        regions=("CE",),
        causes=("digitacao",),
        topics=("topico_a",),
        start_date=date(2026, 1, 1),
        end_date=date(2026, 2, 1),
        only_refaturamento=True,
        include_total=True,
        theme="dark",
    )

    params = filters_to_query_params(filters)
    restored = filters_from_query_params(params, options)

    assert params["regiao"] == "CE"
    assert restored == filters


def test_invalid_query_dates_are_ignored() -> None:
    options = filter_options(_frame())
    restored = filters_from_query_params({"inicio": "not-a-date"}, options)

    assert restored.start_date == options.min_date


def test_query_params_accept_list_values_and_empty_lists() -> None:
    options = filter_options(_frame())
    restored = filters_from_query_params({"regiao": ["CE"], "causa": []}, options)

    assert restored.regions == ("CE",)
    assert restored.causes == options.causes


def test_presets_update_current_filters() -> None:
    frame = _frame()
    current = default_filters(filter_options(frame))

    assert preset_filters(PRESET_CE, frame, current).regions == ("CE",)
    assert preset_filters(PRESET_REFAT, frame, current).only_refaturamento is True
    last_30 = preset_filters(PRESET_LAST_30, frame, current)
    assert last_30.start_date == date(2026, 1, 21)
    assert preset_filters("Manual", frame, current) == current


def test_active_filter_chips_and_markup() -> None:
    options = filter_options(_frame())
    filters = DashboardFilters(
        regions=("CE",),
        causes=("digitacao",),
        topics=("topico_a",),
        only_refaturamento=True,
        theme="dark",
    )
    normalized = normalize_filters(filters, options)
    chips = active_filter_chips(normalized, options)
    html = chips_markdown(chips)

    assert "Região: CE" in chips
    assert "Causas: 1 selecionadas" in chips
    assert "Tópicos: 1 selecionados" in chips
    assert "Somente refaturamento" in chips
    assert "Tema escuro" in chips
    assert html.count("enel-chip") == len(chips)
    assert "Sem filtros restritivos" in chips_markdown(())
