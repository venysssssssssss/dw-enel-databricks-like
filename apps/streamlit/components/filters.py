"""Persistent filters, presets and query-param helpers for the dashboard."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date, timedelta
from typing import TYPE_CHECKING, Any

import pandas as pd

if TYPE_CHECKING:
    from collections.abc import Mapping

DEFAULT_FILTERS_KEY = "dashboard_filters"
PRESET_LAST_30 = "Últimos 30 dias"
PRESET_CE = "CE · Grupo operacional"
PRESET_REFAT = "Ordens com refaturamento"


@dataclass(frozen=True, slots=True)
class FilterOptions:
    regions: tuple[str, ...]
    causes: tuple[str, ...]
    topics: tuple[str, ...]
    min_date: date | None
    max_date: date | None


@dataclass(frozen=True, slots=True)
class DashboardFilters:
    regions: tuple[str, ...] = ()
    causes: tuple[str, ...] = ()
    topics: tuple[str, ...] = ()
    start_date: date | None = None
    end_date: date | None = None
    only_refaturamento: bool = False
    include_total: bool = False
    theme: str = "light"


def filter_options(frame: pd.DataFrame) -> FilterOptions:
    dates = pd.to_datetime(frame.get("data_ingresso"), errors="coerce")
    valid_dates = dates.dropna()
    regions = frame.get("regiao", pd.Series(dtype=str)).dropna().astype(str).unique()
    causes = frame.get("causa_canonica", pd.Series(dtype=str)).dropna().astype(str).unique()
    topics = frame.get("topic_name", pd.Series(dtype=str)).dropna().astype(str).unique()
    return FilterOptions(
        regions=tuple(sorted(regions)),
        causes=tuple(sorted(causes)),
        topics=tuple(sorted(topics)),
        min_date=valid_dates.min().date() if not valid_dates.empty else None,
        max_date=valid_dates.max().date() if not valid_dates.empty else None,
    )


def default_filters(options: FilterOptions, *, include_total: bool = False) -> DashboardFilters:
    return DashboardFilters(
        regions=options.regions,
        causes=options.causes,
        topics=options.topics,
        start_date=options.min_date,
        end_date=options.max_date,
        include_total=include_total,
    )


def normalize_filters(filters: DashboardFilters, options: FilterOptions) -> DashboardFilters:
    regions = (
        tuple(value for value in filters.regions if value in options.regions) or options.regions
    )
    causes = tuple(value for value in filters.causes if value in options.causes) or options.causes
    topics = tuple(value for value in filters.topics if value in options.topics) or options.topics
    start = filters.start_date or options.min_date
    end = filters.end_date or options.max_date
    if start and end and start > end:
        start, end = end, start
    if start and options.min_date:
        start = max(start, options.min_date)
    if end and options.max_date:
        end = min(end, options.max_date)
    theme = "dark" if filters.theme == "dark" else "light"
    return replace(
        filters,
        regions=regions,
        causes=causes,
        topics=topics,
        start_date=start,
        end_date=end,
        theme=theme,
    )


def apply_dashboard_filters(frame: pd.DataFrame, filters: DashboardFilters) -> pd.DataFrame:
    if frame.empty:
        return frame.copy()
    mask = pd.Series(True, index=frame.index)
    if filters.regions:
        mask &= frame["regiao"].astype(str).isin(filters.regions)
    if filters.causes:
        mask &= frame["causa_canonica"].astype(str).isin(filters.causes)
    if filters.topics:
        mask &= frame["topic_name"].astype(str).isin(filters.topics)
    if filters.start_date or filters.end_date:
        dates = pd.to_datetime(frame["data_ingresso"], errors="coerce")
        if filters.start_date:
            mask &= dates >= pd.Timestamp(filters.start_date)
        if filters.end_date:
            mask &= dates <= pd.Timestamp(filters.end_date)
    if filters.only_refaturamento and "flag_resolvido_com_refaturamento" in frame.columns:
        mask &= frame["flag_resolvido_com_refaturamento"].fillna(False).astype(bool)
    return frame.loc[mask].copy()


def filters_to_query_params(filters: DashboardFilters) -> dict[str, str]:
    params: dict[str, str] = {}
    if filters.regions:
        params["regiao"] = ",".join(filters.regions)
    if filters.causes:
        params["causa"] = ",".join(filters.causes)
    if filters.topics:
        params["topico"] = ",".join(filters.topics)
    if filters.start_date:
        params["inicio"] = filters.start_date.isoformat()
    if filters.end_date:
        params["fim"] = filters.end_date.isoformat()
    if filters.only_refaturamento:
        params["refat"] = "1"
    if filters.include_total:
        params["total"] = "1"
    if filters.theme == "dark":
        params["theme"] = "dark"
    return params


def filters_from_query_params(
    params: Mapping[str, str | list[str] | tuple[str, ...]],
    options: FilterOptions,
) -> DashboardFilters:
    def _value(key: str) -> str:
        raw = params.get(key, "")
        if isinstance(raw, list | tuple):
            return str(raw[0]) if raw else ""
        return str(raw)

    def _split(key: str) -> tuple[str, ...]:
        return tuple(item for item in _value(key).split(",") if item)

    def _date(key: str) -> date | None:
        value = _value(key)
        if not value:
            return None
        try:
            return date.fromisoformat(value)
        except ValueError:
            return None

    return normalize_filters(
        DashboardFilters(
            regions=_split("regiao"),
            causes=_split("causa"),
            topics=_split("topico"),
            start_date=_date("inicio"),
            end_date=_date("fim"),
            only_refaturamento=_value("refat") == "1",
            include_total=_value("total") == "1",
            theme="dark" if _value("theme") == "dark" else "light",
        ),
        options,
    )


def preset_filters(name: str, frame: pd.DataFrame, current: DashboardFilters) -> DashboardFilters:
    options = filter_options(frame)
    if name == PRESET_LAST_30 and options.max_date:
        return normalize_filters(
            replace(
                current,
                start_date=options.max_date - timedelta(days=30),
                end_date=options.max_date,
            ),
            options,
        )
    if name == PRESET_CE:
        return normalize_filters(replace(current, regions=("CE",)), options)
    if name == PRESET_REFAT:
        return normalize_filters(replace(current, only_refaturamento=True), options)
    return normalize_filters(current, options)


def active_filter_chips(filters: DashboardFilters, options: FilterOptions) -> tuple[str, ...]:
    chips: list[str] = []
    if set(filters.regions) != set(options.regions):
        chips.append("Região: " + ", ".join(filters.regions))
    if set(filters.causes) != set(options.causes):
        chips.append(f"Causas: {len(filters.causes)} selecionadas")
    if set(filters.topics) != set(options.topics):
        chips.append(f"Tópicos: {len(filters.topics)} selecionados")
    if filters.start_date or filters.end_date:
        chips.append(f"Período: {filters.start_date or 'início'} → {filters.end_date or 'fim'}")
    if filters.only_refaturamento:
        chips.append("Somente refaturamento")
    if filters.theme == "dark":
        chips.append("Tema escuro")
    return tuple(chips)


def chips_markdown(chips: tuple[str, ...]) -> str:
    if not chips:
        return '<span class="enel-chip">Sem filtros restritivos</span>'
    return "".join(f'<span class="enel-chip">{chip}</span>' for chip in chips)


def render_sidebar_filters(
    st: Any,
    frame: pd.DataFrame,
    *,
    include_total: bool,
) -> DashboardFilters:  # pragma: no cover - exercised by Streamlit smoke/e2e.
    options = filter_options(frame)
    query_filters = filters_from_query_params(dict(st.query_params), options)
    current = st.session_state.get(DEFAULT_FILTERS_KEY, query_filters)
    if not isinstance(current, DashboardFilters):
        current = query_filters
    current = normalize_filters(replace(current, include_total=include_total), options)

    st.sidebar.subheader("Filtros persistentes")
    preset = st.sidebar.radio(
        "Presets",
        ["Manual", PRESET_LAST_30, PRESET_CE, PRESET_REFAT],
        horizontal=False,
        help="Atalhos que atualizam o filtro compartilhado entre abas.",
    )
    if preset != "Manual":
        current = preset_filters(preset, frame, current)

    regions = tuple(
        st.sidebar.multiselect("Região", options.regions, default=list(current.regions))
    )
    causes = tuple(
        st.sidebar.multiselect(
            "Causa canônica",
            options.causes,
            default=list(current.causes),
            help="Label consolidado pela taxonomia e fallback de IA.",
        )
    )
    topics = tuple(
        st.sidebar.multiselect(
            "Tópico IA",
            options.topics,
            default=list(current.topics),
            help="Tópico BERTopic descoberto nos textos livres.",
        )
    )
    start = st.sidebar.date_input(
        "Início",
        value=current.start_date,
        min_value=options.min_date,
        max_value=options.max_date,
    )
    end = st.sidebar.date_input(
        "Fim",
        value=current.end_date,
        min_value=options.min_date,
        max_value=options.max_date,
    )
    only_refat = st.sidebar.toggle("Somente refaturamento", value=current.only_refaturamento)
    theme_dark = st.sidebar.toggle("Dark mode", value=current.theme == "dark")

    updated = normalize_filters(
        DashboardFilters(
            regions=regions,
            causes=causes,
            topics=topics,
            start_date=start if isinstance(start, date) else None,
            end_date=end if isinstance(end, date) else None,
            only_refaturamento=only_refat,
            include_total=include_total,
            theme="dark" if theme_dark else "light",
        ),
        options,
    )
    st.session_state[DEFAULT_FILTERS_KEY] = updated
    st.query_params.update(filters_to_query_params(updated))

    st.sidebar.markdown("**Filtros ativos**")
    st.sidebar.markdown(
        chips_markdown(active_filter_chips(updated, options)),
        unsafe_allow_html=True,
    )
    if st.sidebar.button("Limpar filtros", use_container_width=True):
        updated = default_filters(options, include_total=include_total)
        st.session_state[DEFAULT_FILTERS_KEY] = updated
        st.query_params.clear()
        st.rerun()
    return updated
