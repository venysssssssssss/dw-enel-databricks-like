"""Shared abstractions for feature builders."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import pandas as pd

from src.common.logging import get_logger


@dataclass(slots=True)
class FeatureBuilderContext:
    observation_date: date


class BaseFeatureBuilder:
    feature_set_name: str = ""
    entity_key: str = ""
    target_columns: tuple[str, ...] = ()

    def __init__(self, observation_date: date) -> None:
        self.context = FeatureBuilderContext(observation_date=observation_date)
        self.logger = get_logger(self.__class__.__name__)

    @property
    def observation_date(self) -> date:
        return self.context.observation_date

    def validate_columns(self, frame: pd.DataFrame, required_columns: list[str]) -> None:
        missing = [column for column in required_columns if column not in frame.columns]
        if missing:
            missing_cols = ", ".join(sorted(missing))
            raise ValueError(f"Colunas obrigatorias ausentes para {self.feature_set_name}: {missing_cols}")
