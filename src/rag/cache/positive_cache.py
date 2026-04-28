"""Positive Cache: lookup determinístico de respostas pré-aprovadas.

Normalização agressiva (case-fold + remoção de aspas/templates + token-set):
captura variantes geradas por templates de avaliação ("Na regional X, como
tratamos ordens do tipo 'Y' parecidas com '...'") sem custo de embedding.
"""

from __future__ import annotations

import hashlib
import logging
import re
import unicodedata
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_QUOTED_RE = re.compile(r"['\"][^'\"]{0,200}['\"]")
_BRACKETED_RE = re.compile(r"\[[^\]]{0,80}\]")
_NUMBER_RE = re.compile(r"\b\d{2,}\b")
_PUNCT_RE = re.compile(r"[\.,;:!\?\(\)\[\]\{\}\"\'\-_/\\]+")
_WHITESPACE_RE = re.compile(r"\s+")
_STOPWORDS = frozenset(
    {
        "a", "o", "os", "as", "um", "uma", "de", "do", "da", "dos", "das", "no", "na",
        "nos", "nas", "em", "para", "por", "que", "com", "como", "qual", "quais",
        "e", "ou", "ao", "à", "às", "se", "tem", "ter", "dada", "dado", "sobre",
    }
)


class PositiveCache:
    """Cache de respostas memorizadas indexadas por hash de token-set."""

    def __init__(self, cache_path: str = "data/rag_train/positive_cache.parquet"):
        self.cache_path = Path(cache_path)
        self.df = None
        self._index: dict[str, dict[str, Any]] = {}
        self._load()

    def _load(self) -> None:
        if not self.cache_path.exists():
            return
        try:
            import pandas as pd

            self.df = pd.read_parquet(self.cache_path)
        except Exception as exc:
            logger.error("Error loading positive cache: %s", exc)
            self.df = None
            return
        if self.df is None or self.df.empty:
            return
        # Pré-indexa em dict para lookup O(1). Aceita colunas legacy `hash`
        # (sha256 da forma normalizada antiga) e a nova `token_hash`.
        for _, row in self.df.iterrows():
            entry = row.to_dict()
            for key in ("token_hash", "hash"):
                value = entry.get(key)
                if value:
                    self._index[str(value)] = entry
        logger.info("Positive cache loaded with %d entries (%d hash keys).",
                    len(self.df), len(self._index))

    def lookup(self, question: str) -> dict[str, Any] | None:
        if not self._index:
            return None
        for digest in self._candidate_hashes(question):
            entry = self._index.get(digest)
            if entry:
                return entry
        return None

    @classmethod
    def _candidate_hashes(cls, question: str) -> list[str]:
        canonical = cls.canonicalize(question)
        token_set = cls.tokenize(question)
        return [
            cls._sha(canonical),
            cls._sha(token_set),
            cls._sha(question.lower().strip()),
        ]

    @staticmethod
    def _sha(value: str) -> str:
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    @staticmethod
    def canonicalize(text: str) -> str:
        """Forma canônica preservando ordem (frase normalizada)."""
        text = unicodedata.normalize("NFKC", text).lower().strip()
        text = _QUOTED_RE.sub("§", text)
        text = _BRACKETED_RE.sub("§", text)
        text = _NUMBER_RE.sub("§", text)
        text = _PUNCT_RE.sub(" ", text)
        return _WHITESPACE_RE.sub(" ", text).strip()

    @classmethod
    def tokenize(cls, text: str) -> str:
        """Token-set canônico (ordenado, sem stopwords)."""
        canonical = cls.canonicalize(text)
        tokens = sorted({tok for tok in canonical.split() if tok and tok not in _STOPWORDS})
        return " ".join(tokens)
