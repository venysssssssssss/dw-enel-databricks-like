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
    normalize_installation,
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

    def sp_installation_details(self, instalacao_id: str) -> dict[str, Any] | None:
        normalized = normalize_installation(pd.Series([instalacao_id])).iloc[0]
        if not normalized:
            return None
        frame = self.load_silver(include_total=False)
        if frame.empty or "regiao" not in frame.columns or "instalacao" not in frame.columns:
            return None
        subset = frame.loc[
            frame["regiao"].astype(str).eq("SP")
            & frame["instalacao"].astype(str).eq(normalized)
        ].copy()
        if subset.empty:
            return None
        subset["procedencia_real"] = (
            subset.get("procedencia_real", pd.Series("NAO_INFORMADA", index=subset.index))
            .fillna("NAO_INFORMADA")
            .astype(str)
        )
        if "fat_reclamada_top" in subset.columns:
            monthly = (
                subset.loc[subset["fat_reclamada_top"].fillna("").astype(str).str.strip().ne("")]
                .groupby("fat_reclamada_top", as_index=False)
                .agg(
                    qtd_ordens=("ordem", "nunique"),
                    valor_medio=("valor_fatura_reclamada_medio", "mean"),
                    valor_max=("valor_fatura_reclamada_max", "max"),
                    tipo_medidor=("tipo_medidor_dominante", _mode_text),
                    assunto_top=("assunto", _mode_text),
                    causa_top=("causa_canonica", _mode_text),
                )
                .sort_values("fat_reclamada_top")
            )
        else:
            monthly = pd.DataFrame()

        return {
            "instalacao": normalized,
            "total_ordens": int(subset["ordem"].nunique()),
            "procedentes": int(subset["procedencia_real"].eq("PROCEDENTE").sum()),
            "improcedentes": int(subset["procedencia_real"].eq("IMPROCEDENTE").sum()),
            "tipos_medidor": _unique_nonempty(subset.get("tipo_medidor_dominante")),
            "assuntos_top": _top_counts(subset, "assunto"),
            "causas_top": _top_counts(subset, "causa_canonica"),
            "faturas": json.loads(monthly.to_json(orient="records")) if not monthly.empty else [],
        }

    def sp_overview_metrics(self) -> dict[str, Any]:
        frame = self.load_silver(include_total=False)
        if frame.empty or "regiao" not in frame.columns:
            return {"total_ordens": 0, "procedentes": 0, "improcedentes": 0}
        subset = frame.loc[frame["regiao"].astype(str).eq("SP")].copy()
        if subset.empty:
            return {"total_ordens": 0, "procedentes": 0, "improcedentes": 0}
        procedencia = (
            subset.get("procedencia_real", pd.Series("NAO_INFORMADA", index=subset.index))
            .fillna("NAO_INFORMADA")
            .astype(str)
        )
        return {
            "total_ordens": int(subset["ordem"].nunique()),
            "procedentes": int(procedencia.eq("PROCEDENTE").sum()),
            "improcedentes": int(procedencia.eq("IMPROCEDENTE").sum()),
            "tipos_medidor": _unique_nonempty(subset.get("tipo_medidor_dominante")),
        }

    def sp_installations_by_meter_type(
        self,
        meter_type: str,
        *,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        needle = meter_type.strip().casefold()
        if not needle:
            return []
        frame = self.load_silver(include_total=False)
        if frame.empty or "regiao" not in frame.columns or "tipo_medidor_dominante" not in frame.columns:
            return []
        subset = frame.loc[
            frame["regiao"].astype(str).eq("SP")
            & frame["tipo_medidor_dominante"].fillna("").astype(str).str.casefold().str.contains(
                needle,
                regex=False,
            )
        ].copy()
        if subset.empty:
            return []
        grouped = (
            subset.groupby("instalacao", as_index=False)
            .agg(
                qtd_ordens=("ordem", "nunique"),
                assunto_top=("assunto", _mode_text),
                causa_top=("causa_canonica", _mode_text),
                tipo_medidor=("tipo_medidor_dominante", _mode_text),
            )
            .sort_values(["qtd_ordens", "instalacao"], ascending=[False, True])
            .head(limit)
        )
        return json.loads(grouped.to_json(orient="records"))

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


def _mode_text(series: pd.Series) -> str:
    values = series.dropna().astype(str).str.strip()
    values = values.loc[values.ne("")]
    if values.empty:
        return ""
    return str(values.value_counts().index[0])


def _top_counts(frame: pd.DataFrame, column: str, *, limit: int = 5) -> list[dict[str, Any]]:
    if column not in frame.columns:
        return []
    grouped = (
        frame.loc[frame[column].fillna("").astype(str).str.strip().ne("")]
        .groupby(column, as_index=False)
        .agg(qtd_ordens=("ordem", "nunique"))
        .sort_values(["qtd_ordens", column], ascending=[False, True])
        .head(limit)
    )
    return json.loads(grouped.to_json(orient="records"))


def _unique_nonempty(series: pd.Series | None) -> list[str]:
    if series is None:
        return []
    values = (
        series.dropna()
        .astype(str)
        .map(str.strip)
        .loc[lambda value: value.ne("")]
        .drop_duplicates()
        .tolist()
    )
    return [str(value) for value in values]
