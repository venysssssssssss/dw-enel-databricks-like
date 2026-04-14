"""Topic discovery for erro de leitura complaints."""

from __future__ import annotations

from dataclasses import dataclass
import re

import pandas as pd
from sklearn.cluster import KMeans
from sklearn.feature_extraction.text import TfidfVectorizer


MAX_TAXONOMY_EXAMPLE_CHARS = 420

DOMAIN_STOPWORDS = {
    "a",
    "acordo",
    "ao",
    "aos",
    "apos",
    "analise",
    "apresentada",
    "as",
    "base",
    "celular",
    "cliente",
    "clientes",
    "clt",
    "com",
    "conf",
    "conforme",
    "conta",
    "da",
    "das",
    "de",
    "demais",
    "dia",
    "do",
    "dos",
    "dt",
    "email",
    "em",
    "erro",
    "erro leitura",
    "entenda",
    "esta",
    "fat",
    "fatura",
    "feito",
    "foi",
    "foram",
    "gmtuk",
    "ha",
    "informada",
    "informacoes",
    "informacoes que",
    "informa",
    "inst",
    "instalacao",
    "julgar",
    "julgar necessarias",
    "leped",
    "leitura",
    "lt",
    "mes",
    "na",
    "nas",
    "nao",
    "necessarias",
    "no",
    "nos",
    "ordem",
    "os",
    "para",
    "pela",
    "pelo",
    "periodo",
    "por",
    "que",
    "procedente",
    "realizado",
    "realizada",
    "reclama",
    "ref",
    "refs",
    "referencia",
    "solicitado",
    "solicita",
    "seu",
    "sistema",
    "sua",
    "sua conta",
    "trata",
    "valor",
    "voce",
    "xx",
}


@dataclass(frozen=True, slots=True)
class TopicModelResult:
    assignments: pd.DataFrame
    taxonomy: pd.DataFrame
    backend: str


class ErroLeituraTopicModelTrainer:
    """Discovers complaint patterns with BERTopic when available and sklearn fallback."""

    def __init__(
        self,
        *,
        min_topic_size: int = 20,
        max_topics: int = 8,
        use_bertopic: bool = False,
        stopwords: set[str] | None = None,
    ) -> None:
        self.min_topic_size = min_topic_size
        self.max_topics = max_topics
        self.use_bertopic = use_bertopic
        self.stopwords = DOMAIN_STOPWORDS if stopwords is None else stopwords

    def train(self, frame: pd.DataFrame, *, key_column: str = "ordem", text_column: str = "texto_completo") -> TopicModelResult:
        if self.use_bertopic:
            try:
                return self._train_bertopic(frame, key_column=key_column, text_column=text_column)
            except ImportError:
                pass
        return self._train_sklearn(frame, key_column=key_column, text_column=text_column)

    def _train_bertopic(self, frame: pd.DataFrame, *, key_column: str, text_column: str) -> TopicModelResult:
        from bertopic import BERTopic

        texts = frame[text_column].fillna("").astype(str).tolist()
        model = BERTopic(min_topic_size=self.min_topic_size, calculate_probabilities=False)
        topics, _ = model.fit_transform(texts)
        assignments = pd.DataFrame({key_column: frame[key_column].astype(str), "topic_id": topics})
        info = model.get_topic_info()
        taxonomy = info.rename(columns={"Topic": "topic_id", "Name": "topic_name", "Count": "topic_size"})
        return TopicModelResult(assignments=assignments, taxonomy=taxonomy, backend="bertopic")

    def _train_sklearn(self, frame: pd.DataFrame, *, key_column: str, text_column: str) -> TopicModelResult:
        texts = [_topic_training_text(value) for value in frame[text_column].fillna("").astype(str).tolist()]
        topic_count = max(1, min(self.max_topics, len(texts), max(1, len(texts) // max(self.min_topic_size, 1))))
        vectorizer = TfidfVectorizer(
            min_df=1,
            ngram_range=(1, 2),
            max_features=2048,
            stop_words=list(self.stopwords),
            token_pattern=r"(?u)\b[a-zA-Z_][a-zA-Z_]{2,}\b",
        )
        matrix = vectorizer.fit_transform(texts)
        if topic_count == 1:
            labels = [0] * len(texts)
        else:
            labels = KMeans(n_clusters=topic_count, random_state=42, n_init=10).fit_predict(matrix).tolist()
        feature_names = vectorizer.get_feature_names_out()
        assignments = pd.DataFrame({key_column: frame[key_column].astype(str), "topic_id": labels})
        taxonomy_rows = []
        for topic_id in sorted(set(labels)):
            indices = [index for index, label in enumerate(labels) if label == topic_id]
            centroid = matrix[indices].mean(axis=0).A1
            top_indices = centroid.argsort()[-5:][::-1]
            keywords = [_safe_keyword(feature_names[index]) for index in top_indices if centroid[index] > 0]
            keywords = [keyword for keyword in keywords if keyword and keyword not in self.stopwords]
            taxonomy_rows.append(
                {
                    "topic_id": topic_id,
                    "topic_name": "_".join(keywords[:3]) or f"topico_{topic_id}",
                    "topic_size": len(indices),
                    "keywords": keywords,
                    "examples": [_taxonomy_example(value) for value in frame.iloc[indices][text_column].head(3).tolist()],
                }
            )
        return TopicModelResult(assignments=assignments, taxonomy=pd.DataFrame(taxonomy_rows), backend="sklearn-kmeans")


def mask_sensitive_text(value: object) -> str:
    text = "" if value is None or pd.isna(value) else str(value)
    text = re.sub(r"\b[\w.+-]+@[\w.-]+\.[a-zA-Z]{2,}\b", "[EMAIL]", text)
    text = re.sub(r"\bbr\d{5,}\b", "br[ID_INTERNO]", text, flags=re.IGNORECASE)
    text = re.sub(r"\bgmtuk\s+[^()*\n\r]{3,80}\s+\(br\[?ID_INTERNO\]?\)", "gmtuk [USUARIO] (br[ID_INTERNO])", text)
    text = re.sub(
        r"\bgmtuk\s+[a-zA-ZÀ-ÿ\s]{3,100}?(?=\s+(?:cliente|clt|reclama|solicita|trata|erro|segue|\*|$))",
        "gmtuk [USUARIO]",
        text,
    )
    text = re.sub(r"(?:\+?55\s*)?(?:\(?\d{2}\)?\s*)?9?\d{4}[-\s]?\d{4}", "[TELEFONE]", text)
    text = re.sub(r"\b\d{5}-?\d{3}\b", "[CEP]", text)
    text = re.sub(r"\b(?:protocolo|prot)\s*[:#-]?\s*\d{6,}\b", "protocolo [PROTOCOLO]", text)
    text = re.sub(r"\b((?:celular|telefone|tel))\s*:\s*\d+\b", r"\1: [TELEFONE]", text)
    return text


def _topic_training_text(value: object) -> str:
    text = mask_sensitive_text(value)
    text = re.sub(r"\[[A-Z_]+\]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _taxonomy_example(value: object) -> str:
    text = mask_sensitive_text(value)
    if len(text) <= MAX_TAXONOMY_EXAMPLE_CHARS:
        return text
    return f"{text[:MAX_TAXONOMY_EXAMPLE_CHARS].rstrip()}..."


def _safe_keyword(value: str) -> str:
    keyword = value.strip().replace(" ", "_")
    keyword = re.sub(r"_+", "_", keyword)
    return keyword.strip("_")
