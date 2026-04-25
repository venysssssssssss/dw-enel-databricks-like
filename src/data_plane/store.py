"""Canonical access point for ENEL silver data, BI views and RAG cards."""

from __future__ import annotations

import json
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any

import pandas as pd

from src.data_plane.enrichment import (
    build_fatura_profile,
    build_medidor_profile,
)
from src.data_plane.versioning import DatasetVersion
from src.data_plane.views import get_view
from src.viz.cache import load_or_build_disk_cache
from src.viz.erro_leitura_dashboard_data import (
    DASHBOARD_SILVER_COLUMNS,
    DEFAULT_FATURA_SP_PATH,
    DEFAULT_MEDIDOR_SP_PATH,
    DEFAULT_SILVER_PATH,
    DEFAULT_TOPIC_ASSIGNMENTS_PATH,
    DEFAULT_TOPIC_TAXONOMY_PATH,
    DEFAULT_TOPIC_TO_CANONICAL_PATH,
    TRAINING_DATA_TYPES,
    prepare_dashboard_frame,
)


@dataclass(frozen=True, slots=True)
class DataStore:
    silver_path: Path = DEFAULT_SILVER_PATH
    topic_assignments_path: Path = DEFAULT_TOPIC_ASSIGNMENTS_PATH
    topic_taxonomy_path: Path = DEFAULT_TOPIC_TAXONOMY_PATH
    topic_to_canonical_path: Path = DEFAULT_TOPIC_TO_CANONICAL_PATH
    medidor_sp_path: Path = DEFAULT_MEDIDOR_SP_PATH
    fatura_sp_path: Path = DEFAULT_FATURA_SP_PATH
    cache_dir: Path = Path(".streamlit/cache")
    default_regions: tuple[str, ...] = ("CE", "SP")

    def version(self) -> DatasetVersion:
        return DatasetVersion.from_paths(
            (
                self.silver_path,
                self.topic_assignments_path,
                self.topic_taxonomy_path,
                self.topic_to_canonical_path,
                self.medidor_sp_path,
                self.fatura_sp_path,
            )
        )

    def load_silver(self, *, include_total: bool = False) -> pd.DataFrame:
        signature = sha256(
            "|".join([self.version().hash, str(include_total), "data-plane-v3"]).encode("utf-8")
        ).hexdigest()
        return load_or_build_disk_cache(
            self.cache_dir,
            "data_plane_silver_frame",
            signature,
            lambda: self._build_silver(include_total=include_total),
        )

    def aggregate(
        self,
        view_id: str,
        filters: dict[str, Any] | None = None,
        *,
        include_total: bool = False,
    ) -> pd.DataFrame:
        view = get_view(view_id)
        frame = self._apply_filters(self.load_silver(include_total=include_total), filters or {})
        return view.run(frame).reset_index(drop=True)

    def aggregate_records(
        self,
        view_id: str,
        filters: dict[str, Any] | None = None,
        *,
        include_total: bool = False,
    ) -> list[dict[str, Any]]:
        frame = self.aggregate(view_id, filters, include_total=include_total)
        return json.loads(frame.to_json(orient="records", date_format="iso"))

    def cards(self, *, regional_scope: str = "CE+SP") -> list[Any]:
        from src.data_plane.cards import build_data_cards

        return build_data_cards(self, regional_scope=regional_scope)

    def _build_silver(self, *, include_total: bool) -> pd.DataFrame:
        if not self.silver_path.exists():
            return pd.DataFrame()
        silver = pd.read_csv(
            self.silver_path,
            dtype=str,
            low_memory=False,
            usecols=lambda column: column in DASHBOARD_SILVER_COLUMNS,
        )
        medidor_profile = build_medidor_profile(self.medidor_sp_path)
        fatura_profile = build_fatura_profile(self.fatura_sp_path)
        if include_total:
            training_frame = self._prepare_frame(
                silver,
                include_total=False,
                medidor_profile=medidor_profile,
                fatura_profile=fatura_profile,
            )
            total_silver = silver.loc[~silver["_data_type"].isin(TRAINING_DATA_TYPES)].copy()
            if total_silver.empty:
                return training_frame
            total_frame = prepare_dashboard_frame(
                total_silver,
                topic_assignments=None,
                topic_taxonomy=None,
                topic_to_canonical=_read_optional_csv(self.topic_to_canonical_path),
                medidor_profile=medidor_profile,
                fatura_profile=fatura_profile,
                include_total=True,
            )
            return pd.concat([training_frame, total_frame], ignore_index=True)
        return self._prepare_frame(
            silver,
            include_total=False,
            medidor_profile=medidor_profile,
            fatura_profile=fatura_profile,
        )

    def _prepare_frame(
        self,
        silver: pd.DataFrame,
        *,
        include_total: bool,
        medidor_profile: pd.DataFrame | None = None,
        fatura_profile: pd.DataFrame | None = None,
    ) -> pd.DataFrame:
        return prepare_dashboard_frame(
            silver,
            topic_assignments=_read_optional_csv(self.topic_assignments_path),
            topic_taxonomy=_read_optional_json(self.topic_taxonomy_path),
            topic_to_canonical=_read_optional_csv(self.topic_to_canonical_path),
            medidor_profile=medidor_profile,
            fatura_profile=fatura_profile,
            include_total=include_total,
        )

    def _apply_filters(self, frame: pd.DataFrame, filters: dict[str, Any]) -> pd.DataFrame:
        if frame.empty:
            return frame.copy()
        filtered = frame.copy()
        if "regiao" in filtered.columns and self.default_regions:
            allowed_default = {str(region) for region in self.default_regions}
            filtered = filtered.loc[filtered["regiao"].astype(str).isin(allowed_default)]
        if not filters:
            return filtered
        for column in (
            "regiao",
            "tipo_origem",
            "causa_canonica",
            "causa_canonica_confidence",
            "topic_name",
            "status",
            "assunto",
        ):
            if column not in filtered.columns or column not in filters:
                continue
            values = filters[column]
            if values in (None, "", []):
                continue
            allowed = {str(values)} if isinstance(values, str) else {str(value) for value in values}
            filtered = filtered.loc[filtered[column].astype(str).isin(allowed)]
        if "start_date" in filters and "data_ingresso" in filtered.columns:
            start = pd.to_datetime(filters["start_date"], errors="coerce")
            if pd.notna(start):
                filtered = filtered.loc[filtered["data_ingresso"].ge(start)]
        if "end_date" in filters and "data_ingresso" in filtered.columns:
            end = pd.to_datetime(filters["end_date"], errors="coerce")
            if pd.notna(end):
                filtered = filtered.loc[filtered["data_ingresso"].le(end)]
        return filtered


def _read_optional_csv(path: Path) -> pd.DataFrame | None:
    if not path.exists():
        return None
    return pd.read_csv(path)


def _read_optional_json(path: Path) -> pd.DataFrame | None:
    if not path.exists():
        return None
    return pd.read_json(path)
