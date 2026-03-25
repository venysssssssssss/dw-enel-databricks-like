"""Model training pipelines for Sprints 11-12."""

from src.ml.models.anomalia_model import AnomaliaModelTrainer
from src.ml.models.atraso_model import AtrasoModelTrainer
from src.ml.models.inadimplencia_model import InadimplenciaModelTrainer
from src.ml.models.metas_model import MetasModelTrainer
from src.ml.models.registry import LocalModelRegistry

__all__ = [
    "AnomaliaModelTrainer",
    "AtrasoModelTrainer",
    "InadimplenciaModelTrainer",
    "LocalModelRegistry",
    "MetasModelTrainer",
]
