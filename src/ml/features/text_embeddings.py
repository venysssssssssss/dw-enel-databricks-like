"""Text embeddings for erro de leitura complaints."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer

from src.common.config import get_settings


@dataclass(frozen=True, slots=True)
class EmbeddingResult:
    frame: pd.DataFrame
    backend: str
    dimensions: int


class TextEmbeddingBuilder:
    """Builds multilingual embeddings with optional sentence-transformers backend."""

    def __init__(
        self,
        *,
        model_name: str = "paraphrase-multilingual-MiniLM-L12-v2",
        dimensions: int = 32,
        batch_size: int = 32,
        use_sentence_transformers: bool = False,
    ) -> None:
        self.model_name = model_name
        self.dimensions = dimensions
        self.batch_size = batch_size
        self.use_sentence_transformers = use_sentence_transformers
        self._vectorizer: TfidfVectorizer | None = None
        self._svd: TruncatedSVD | None = None

    def build(self, frame: pd.DataFrame, *, key_column: str = "ordem", text_column: str = "texto_completo") -> EmbeddingResult:
        if key_column not in frame.columns or text_column not in frame.columns:
            raise ValueError(f"Colunas obrigatorias ausentes para embeddings: {key_column}, {text_column}")
        texts = frame[text_column].fillna("").astype(str).tolist()
        if self.use_sentence_transformers:
            try:
                embeddings = self._sentence_transformer_embeddings(texts)
                backend = "sentence-transformers"
            except ImportError:
                embeddings = self._tfidf_svd_embeddings(texts)
                backend = "tfidf-svd"
        else:
            embeddings = self._tfidf_svd_embeddings(texts)
            backend = "tfidf-svd"

        embedding_columns = [f"embedding_{index:03d}" for index in range(embeddings.shape[1])]
        result = pd.DataFrame(embeddings, columns=embedding_columns)
        result.insert(0, key_column, frame[key_column].astype(str).to_numpy())
        if "dt_ingresso" in frame.columns:
            result["dt_ingresso"] = frame["dt_ingresso"].to_numpy()
        if "_source_region" in frame.columns:
            result["_source_region"] = frame["_source_region"].to_numpy()
        if "causa_raiz" in frame.columns:
            result["causa_raiz"] = frame["causa_raiz"].to_numpy()
        return EmbeddingResult(frame=result, backend=backend, dimensions=embeddings.shape[1])

    def save(self, result: EmbeddingResult, output_path: Path | None = None) -> Path:
        settings = get_settings()
        target = output_path or settings.feature_store_path / "erro_leitura_embeddings" / "dataset.parquet"
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            result.frame.to_parquet(target, index=False)
            return target
        except Exception:
            fallback = target.with_suffix(".csv")
            result.frame.to_csv(fallback, index=False)
            return fallback

    def _sentence_transformer_embeddings(self, texts: list[str]) -> np.ndarray:
        from sentence_transformers import SentenceTransformer

        model = SentenceTransformer(self.model_name)
        return np.asarray(
            model.encode(texts, batch_size=self.batch_size, normalize_embeddings=True, show_progress_bar=False),
            dtype=float,
        )

    def _tfidf_svd_embeddings(self, texts: list[str]) -> np.ndarray:
        if self._vectorizer is not None:
            matrix = self._vectorizer.transform(texts)
            if self._svd is not None:
                embeddings = self._svd.transform(matrix)
                norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
                return embeddings / np.where(norms == 0.0, 1.0, norms)
            return matrix.toarray().astype(float)

        self._vectorizer = TfidfVectorizer(min_df=1, ngram_range=(1, 2), max_features=4096)
        matrix = self._vectorizer.fit_transform(texts)
        max_components = max(1, min(self.dimensions, matrix.shape[0] - 1, matrix.shape[1] - 1))
        if max_components < 2:
            return matrix.toarray().astype(float)
        self._svd = TruncatedSVD(n_components=max_components, random_state=42)
        embeddings = self._svd.fit_transform(matrix)
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        return embeddings / np.where(norms == 0.0, 1.0, norms)
