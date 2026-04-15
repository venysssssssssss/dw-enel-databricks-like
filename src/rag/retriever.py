"""Retrieval híbrido: ChromaDB cosine (top-K) + rerank opcional por LLM.

Em CPU pura evitamos rerank LLM por default (custa segundos). Em vez disso
aplicamos **rerank lexical barato** (BM25-like via Jaccard de tokens) para
quebrar empates do cosine — soma sinal semântico com sinal superficial sem
custo de inferência.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from src.rag.config import RagConfig

_TOKEN_RE = re.compile(r"[\wÀ-ÿ]+", re.UNICODE)


@dataclass(frozen=True, slots=True)
class Passage:
    chunk_id: str
    text: str
    source_path: str
    section: str
    doc_type: str
    sprint_id: str
    anchor: str
    score: float

    def citation(self) -> str:
        anchor = f"#{self.anchor}" if self.anchor else ""
        return f"[fonte: {self.source_path}{anchor}]"


def _tokens(text: str) -> set[str]:
    return {t.lower() for t in _TOKEN_RE.findall(text) if len(t) > 2}


def lexical_overlap(query: str, passage: str) -> float:
    q = _tokens(query)
    p = _tokens(passage)
    if not q or not p:
        return 0.0
    return len(q & p) / len(q | p)


class HybridRetriever:
    """Retrieval cosine-first, re-scoring híbrido (cosine + lexical)."""

    def __init__(self, config: RagConfig) -> None:
        self.config = config
        self._collection = None
        self._embed_fn = None

    def _ensure_ready(self) -> None:
        if self._collection is not None:
            return
        try:
            import chromadb
        except ImportError as exc:
            raise RuntimeError(
                "chromadb não instalado. Rode: pip install -e '.[rag]'"
            ) from exc
        from src.rag.ingestion import _load_embedder

        path = self.config.chromadb_path
        if not path.exists():
            raise FileNotFoundError(
                f"ChromaDB vazio em {path}. Rode: "
                "python scripts/build_rag_corpus.py --rebuild"
            )
        client = chromadb.PersistentClient(path=str(path))
        self._collection = client.get_collection(self.config.collection_name)
        self._embed_fn = _load_embedder(self.config.embedding_model)

    def retrieve(
        self,
        query: str,
        *,
        k: int | None = None,
        doc_types: list[str] | None = None,
    ) -> list[Passage]:
        self._ensure_ready()
        k_eff = k or self.config.retrieval_k
        query_embedding = self._embed_fn([query])[0]  # type: ignore[misc]
        where = {"doc_type": {"$in": doc_types}} if doc_types else None
        result = self._collection.query(  # type: ignore[union-attr]
            query_embeddings=[query_embedding],
            n_results=k_eff,
            where=where,
        )
        ids = result.get("ids", [[]])[0]
        docs = result.get("documents", [[]])[0]
        metas = result.get("metadatas", [[]])[0]
        dists = result.get("distances", [[]])[0]

        passages: list[Passage] = []
        for cid, text, meta, dist in zip(ids, docs, metas, dists, strict=False):
            cos_sim = max(0.0, 1.0 - float(dist))  # chroma cosine retorna distance
            lex = lexical_overlap(query, text)
            # Combina cosine (peso 0.75) com lexical (peso 0.25): ganho consistente
            # em consultas com entidades nomeadas (ACF, ASF, GD).
            score = 0.75 * cos_sim + 0.25 * lex
            passages.append(
                Passage(
                    chunk_id=cid,
                    text=text,
                    source_path=(meta or {}).get("source_path", ""),
                    section=(meta or {}).get("section", ""),
                    doc_type=(meta or {}).get("doc_type", ""),
                    sprint_id=(meta or {}).get("sprint_id", ""),
                    anchor=(meta or {}).get("anchor", ""),
                    score=score,
                )
            )
        passages.sort(key=lambda p: p.score, reverse=True)
        return passages

    def top_passages(
        self,
        query: str,
        *,
        top_n: int | None = None,
        doc_types: list[str] | None = None,
    ) -> list[Passage]:
        top = top_n or self.config.rerank_top_n
        return self.retrieve(query, k=self.config.retrieval_k, doc_types=doc_types)[:top]


def route_doc_types(query: str) -> list[str] | None:
    """Heurística de roteamento: reduz o espaço de busca por palavra-chave.

    Objetivo: enviar menos chunks ao LLM quando a intenção é clara.
    """
    q = query.lower()
    analytics_terms = (
        "quantos", "quantas", "volume", "total de", "percentual", "porcentagem",
        "top ", "ranking", "maior", "mais frequente", "evolução", "mensal",
        "ceará", " ce ", " ce?", " ce.", " sp ", " sp?", " sp.", "são paulo",
        "reclamações", "reclamacoes", "causa-raiz", "causa raiz", "assunto",
    )
    if any(term in q for term in analytics_terms):
        return ["data", "business", "viz"]
    if any(term in q for term in ("sprint", "entregável", "deliverable")):
        return ["sprint"]
    if any(term in q for term in ("acf", "asf", "refatur", "religa", "grupo b", "grupo a", "gd ")):
        return ["data", "business", "viz"]
    if any(term in q for term in ("modelo", "predict", "feature", "isolation", "lightgbm", "xgboost")):
        return ["ml"]
    if any(term in q for term in ("endpoint", "fastapi", "api ", "rota")):
        return ["api"]
    if any(term in q for term in ("bronze", "silver", "gold", "ingestão", "spark", "iceberg")):
        return ["architecture"]
    if any(term in q for term in ("dashboard", "streamlit", "plotly", "aba", "filtro")):
        return ["viz"]
    return None


def check_stub_corpus(path: Path) -> bool:
    """Retorna True se ChromaDB está populado; usado para mostrar CTA na UI."""
    return path.exists() and any(path.glob("*.sqlite*"))
