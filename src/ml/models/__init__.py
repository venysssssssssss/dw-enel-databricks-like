"""Lazy model training exports for Sprints 11-13.

Importing one lightweight model module should not import the full ML stack.
"""

from __future__ import annotations

from typing import Any

_EXPORTS = {
    "AnomaliaModelTrainer": ("src.ml.models.anomalia_model", "AnomaliaModelTrainer"),
    "AtrasoModelTrainer": ("src.ml.models.atraso_model", "AtrasoModelTrainer"),
    "ErroLeituraAnomalyDetector": (
        "src.ml.models.erro_leitura_anomaly",
        "ErroLeituraAnomalyDetector",
    ),
    "ErroLeituraClassifierTrainer": (
        "src.ml.models.erro_leitura_classifier",
        "ErroLeituraClassifierTrainer",
    ),
    "ErroLeituraTopicModelTrainer": (
        "src.ml.models.erro_leitura_topic_model",
        "ErroLeituraTopicModelTrainer",
    ),
    "InadimplenciaModelTrainer": ("src.ml.models.inadimplencia_model", "InadimplenciaModelTrainer"),
    "KeywordErroLeituraClassifier": (
        "src.ml.models.erro_leitura_classifier",
        "KeywordErroLeituraClassifier",
    ),
    "LocalModelRegistry": ("src.ml.models.registry", "LocalModelRegistry"),
    "MetasModelTrainer": ("src.ml.models.metas_model", "MetasModelTrainer"),
}

__all__ = sorted(_EXPORTS)


def __getattr__(name: str) -> Any:
    if name not in _EXPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_name, attr_name = _EXPORTS[name]
    from importlib import import_module

    value = getattr(import_module(module_name), attr_name)
    globals()[name] = value
    return value
