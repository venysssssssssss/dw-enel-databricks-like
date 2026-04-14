"""Semi-supervised classifier for erro de leitura root causes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, f1_score
from sklearn.model_selection import TimeSeriesSplit
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import LabelEncoder

from src.ml.features.text_embeddings import TextEmbeddingBuilder


KEYWORD_TAXONOMY = {
    "acesso_negado": ["acesso", "portao", "fechado", "impedido", "local dificil"],
    "leitura_estimada": ["estimada", "media", "sem leitura", "leitura nao realizada"],
    "medidor_danificado": ["medidor", "quebrado", "danificado", "defeito", "visor"],
    "endereco_divergente": ["endereco", "divergente", "localizacao", "rua", "bairro"],
    "digitacao": ["digitacao", "valor incorreto", "leitura errada", "numero errado"],
    "leitura_confirmada": ["foto", "comprovacao", "leitura apresentada", "leitura confirmada"],
    "refaturamento": ["refatur", "fatura corrigida", "cancelada", "nova fatura"],
    "tipologia_incorreta": ["tipologia errada", "tipologia incorreta", "outra area", "nova ordem"],
}

CANONICAL_LABEL_PATTERNS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("digitacao", ("digitacao", "digitação", "valor_incorreto", "numero_errado")),
    ("leitura_estimada", ("media", "média", "estimada", "faturamento_por_media", "faturamento_por_média")),
    ("medidor_danificado", ("medidor", "defeito", "danificado", "visor")),
    ("acesso_negado", ("acesso", "impedimento", "portao", "portão")),
    ("endereco_divergente", ("endereco", "endereço", "divergente", "localizacao", "localização")),
    ("refaturamento", ("refatur", "fatura_corrigida", "cancelada")),
    ("leitura_confirmada", ("confirmada", "foto", "comprovacao", "comprovação")),
    ("tipologia_incorreta", ("tipologia", "outra_area", "outra_área")),
)


@dataclass(frozen=True, slots=True)
class ErroLeituraTrainingResult:
    macro_f1: float
    classes: tuple[str, ...]
    backend: str
    report: dict[str, Any]


class KeywordErroLeituraClassifier:
    def predict_proba(self, texts: list[str]) -> list[dict[str, float]]:
        results = []
        for text in texts:
            lowered = text.casefold()
            scores = {}
            for label, keywords in KEYWORD_TAXONOMY.items():
                scores[label] = float(sum(1 for keyword in keywords if keyword in lowered))
            if max(scores.values(), default=0.0) == 0.0:
                scores = {label: 1.0 for label in KEYWORD_TAXONOMY}
            total = sum(scores.values()) or 1.0
            results.append({label: value / total for label, value in scores.items()})
        return results

    def classify(self, text: str) -> dict[str, Any]:
        probabilities = self.predict_proba([text])[0]
        top3 = sorted(probabilities.items(), key=lambda item: item[1], reverse=True)[:3]
        return {
            "classe": top3[0][0],
            "probabilidade": round(top3[0][1], 4),
            "top3": [{"classe": label, "probabilidade": round(probability, 4)} for label, probability in top3],
        }


class ErroLeituraClassifierTrainer:
    """Trains a calibrated multiclass classifier over text embeddings."""

    def __init__(self, embedding_builder: TextEmbeddingBuilder | None = None) -> None:
        self.embedding_builder = embedding_builder or TextEmbeddingBuilder()
        self.keyword_classifier = KeywordErroLeituraClassifier()
        self.label_encoder = LabelEncoder()
        self.model: Any | None = None

    def weak_labels(self, frame: pd.DataFrame) -> pd.Series:
        labels = frame.get("causa_raiz", pd.Series(index=frame.index, dtype=object)).fillna("").astype(str)
        normalized = labels.str.strip().str.casefold().str.replace(r"\s+", "_", regex=True)
        inferred = pd.Series(
            [self.keyword_classifier.classify(text)["classe"] for text in frame["texto_completo"].fillna("")],
            index=frame.index,
        )
        canonical = normalized.map(canonical_label)
        missing = canonical.isna()
        canonical.loc[missing] = inferred.loc[missing]
        return canonical

    def train(self, frame: pd.DataFrame) -> ErroLeituraTrainingResult:
        if len(frame) < 4:
            raise ValueError("Sao necessarias pelo menos 4 linhas para treinar o classificador de erro leitura.")
        labels = self.weak_labels(frame)
        embeddings = self.embedding_builder.build(frame).frame
        feature_columns = [column for column in embeddings.columns if column.startswith("embedding_")]
        target = self.label_encoder.fit_transform(labels)
        base_model = LogisticRegression(max_iter=500, class_weight="balanced")
        min_class_count = int(pd.Series(target).value_counts().min())
        if min_class_count >= 2:
            self.model = CalibratedClassifierCV(base_model, method="sigmoid", cv=2)
        else:
            self.model = base_model
        self.model.fit(embeddings[feature_columns], target)

        macro_scores: list[float] = []
        splitter = TimeSeriesSplit(n_splits=min(3, max(2, len(frame) // 3)))
        for train_index, test_index in splitter.split(embeddings):
            pipeline = Pipeline([("model", LogisticRegression(max_iter=500, class_weight="balanced"))])
            pipeline.fit(embeddings.iloc[train_index][feature_columns], target[train_index])
            prediction = pipeline.predict(embeddings.iloc[test_index][feature_columns])
            macro_scores.append(float(f1_score(target[test_index], prediction, average="macro", zero_division=0)))

        fitted_predictions = self.model.predict(embeddings[feature_columns])
        report = classification_report(
            target,
            fitted_predictions,
            target_names=self.label_encoder.classes_,
            output_dict=True,
            zero_division=0,
        )
        return ErroLeituraTrainingResult(
            macro_f1=float(np.mean(macro_scores)) if macro_scores else 0.0,
            classes=tuple(self.label_encoder.classes_.tolist()),
            backend="logistic-regression-calibrated",
            report=report,
        )

    def classify(self, text: str) -> dict[str, Any]:
        if self.model is None:
            return self.keyword_classifier.classify(text)
        frame = pd.DataFrame({"ordem": ["ad_hoc"], "texto_completo": [text]})
        embeddings = self.embedding_builder.build(frame).frame
        feature_columns = [column for column in embeddings.columns if column.startswith("embedding_")]
        probabilities = self.model.predict_proba(embeddings[feature_columns])[0]
        top_indices = np.argsort(probabilities)[-3:][::-1]
        top3 = [
            {"classe": self.label_encoder.classes_[index], "probabilidade": round(float(probabilities[index]), 4)}
            for index in top_indices
        ]
        return {"classe": top3[0]["classe"], "probabilidade": top3[0]["probabilidade"], "top3": top3}


def canonical_label(value: object) -> str | None:
    if value is None or pd.isna(value):
        return None
    text = str(value).strip().casefold()
    if not text or text == "nan":
        return None
    for label, patterns in CANONICAL_LABEL_PATTERNS:
        if any(pattern in text for pattern in patterns):
            return label
    if text in KEYWORD_TAXONOMY:
        return text
    return None
