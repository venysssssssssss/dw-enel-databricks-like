"""Retrieval híbrido: ChromaDB cosine (top-K) + rerank opcional por LLM.

Em CPU pura evitamos rerank LLM por default (custa segundos). Em vez disso
aplicamos **rerank lexical barato** (BM25-like via Jaccard de tokens) para
quebrar empates do cosine — soma sinal semântico com sinal superficial sem
custo de inferência.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from pathlib import Path

    from src.rag.config import RagConfig

_TOKEN_RE = re.compile(r"[\wÀ-ÿ]+", re.UNICODE)
_QUERY_EXPANSION_HINTS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("reincid", ("recorrência", "repetição", "mesma instalação")),
    ("sazon", ("mensal", "pico", "tendência temporal")),
    ("assunto", ("tema", "categoria de reclamação")),
    ("causa", ("causa-raiz", "motivo")),
    ("motivo", ("causa-raiz", "driver operacional", "recorrência")),
    ("recorrent", ("reincidência", "frequência", "série mensal")),
    ("instala", ("uc", "unidade consumidora")),
    ("medidor", ("tipo de medidor", "digital", "analógico", "ciclométrico")),
    ("digital", ("medidor digital", "causa por tipo", "percentual no tipo")),
    (
        "refaturamento produtos",
        ("ce total", "assunto causa", "refaturamento corretivo"),
    ),
    ("fatura", ("valor da fatura", "emissão", "vencimento")),
)


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
    dataset_version: str = ""
    region: str = "CE+SP"
    scope: str = "global"
    data_source: str = "docs.markdown"

    def citation(self) -> str:
        anchor = f"#{self.anchor}" if self.anchor else ""
        return f"[fonte: {self.source_path}{anchor}]"


def _tokens(text: str) -> set[str]:
    return {t.lower() for t in _TOKEN_RE.findall(text) if len(t) > 2}


def lexical_overlap(query: str, passage: str) -> float:
    """Sinal lexical para 1 passagem.

    Mantida para compatibilidade. Para >1 passagem, prefira `lexical_scores`
    que faz batch (IDF cross-doc correto e ~30× mais rápido via Rust).
    """
    return lexical_scores(query, [passage])[0] if passage else 0.0


def lexical_scores(query: str, passages: list[str]) -> list[float]:
    """Calcula sinal lexical para N passagens em batch.

    Tenta `enel_core.bm25_score` (Rust paralelo, IDF correto cross-doc) e
    cai para Jaccard puro-Python sem quebrar o pipeline.
    """
    if not passages:
        return []
    try:
        import enel_core

        raw = enel_core.bm25_score(query, list(passages))
        if not raw:
            return [0.0] * len(passages)
        # Normaliza para [0, 1] dividindo pelo maior score do batch — mantém
        # comparabilidade com o sinal cosine (que também vive nesse intervalo).
        peak = max(raw) or 1.0
        return [max(0.0, float(value) / peak) for value in raw]
    except Exception:
        pass
    q_tokens = _tokens(query)
    if not q_tokens:
        return [0.0] * len(passages)
    out: list[float] = []
    for passage in passages:
        p_tokens = _tokens(passage)
        if not p_tokens:
            out.append(0.0)
            continue
        out.append(len(q_tokens & p_tokens) / len(q_tokens | p_tokens))
    return out


class HybridRetriever:
    """Retrieval cosine-first, re-scoring híbrido (cosine + lexical)."""

    def __init__(self, config: RagConfig) -> None:
        self.config = config
        self._collection = None
        self._embed_fn = None
        self._reranker = None

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
        dataset_version: str | None = None,
        region: Literal["CE", "SP", "CE+SP"] | None = None,
    ) -> list[Passage]:
        self._ensure_ready()
        k_eff = k or self.config.retrieval_k
        expanded_query = _expand_query(query) if self.config.query_expansion_enabled else query
        query_embedding = self._embed_fn([expanded_query])[0]  # type: ignore[misc]
        where_clauses: list[dict[str, object]] = []
        if doc_types:
            where_clauses.append({"doc_type": {"$in": doc_types}})
        if dataset_version:
            where_clauses.append({"dataset_version": dataset_version})
        if region == "CE":
            where_clauses.append({"region": {"$in": ["CE", "CE+SP"]}})
        elif region == "SP":
            where_clauses.append({"region": {"$in": ["SP", "CE+SP"]}})
        elif region == "CE+SP":
            where_clauses.append({"region": {"$in": ["CE", "SP", "CE+SP"]}})

        if len(where_clauses) == 1:
            where_filter = where_clauses[0]
        elif where_clauses:
            where_filter = {"$and": where_clauses}
        else:
            where_filter = None
        result = self._collection.query(  # type: ignore[union-attr]
            query_embeddings=[query_embedding],
            n_results=k_eff,
            where=where_filter,
        )
        ids = result.get("ids", [[]])[0]
        docs = result.get("documents", [[]])[0]
        metas = result.get("metadatas", [[]])[0]
        dists = result.get("distances", [[]])[0]

        # Batch BM25 cross-doc: 1 chamada Rust em vez de N (IDF correto + paralelo).
        lex_scores = lexical_scores(expanded_query, list(docs))

        passages: list[Passage] = []
        for cid, text, meta, dist, lex in zip(
            ids, docs, metas, dists, lex_scores, strict=False
        ):
            cos_sim = max(0.0, 1.0 - float(dist))  # chroma cosine retorna distance
            # Combina cosine com lexical para preservar sinônimos PT-BR sem
            # perder correspondência exata de termos de negócio.
            score = 0.60 * cos_sim + 0.40 * lex
            anchor = (meta or {}).get("anchor", "")
            score += _intent_anchor_bonus(query, anchor)
            score += _region_anchor_bonus(region, anchor)
            score += _query_structure_bonus(query, anchor)
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
                    dataset_version=(meta or {}).get("dataset_version", ""),
                    region=(meta or {}).get("region", "CE+SP"),
                    scope=(meta or {}).get("scope", "global"),
                    data_source=(meta or {}).get("data_source", "docs.markdown"),
                )
            )
        passages.sort(key=lambda p: p.score, reverse=True)
        passages = self._rerank(query, passages)
        return passages

    def _rerank(self, query: str, passages: list[Passage]) -> list[Passage]:
        if not passages or not self.config.rerank_enabled:
            return passages
        model = self._load_reranker()
        if model is None:
            return passages
        try:
            pairs = [(query, p.text[:1800]) for p in passages]
            raw_scores = model.predict(pairs)  # type: ignore[attr-defined]
            if not len(raw_scores):
                return passages
            peak = max(float(score) for score in raw_scores) or 1.0
            rescored: list[Passage] = []
            for passage, rr in zip(passages, raw_scores, strict=False):
                rr_norm = max(0.0, float(rr) / peak)
                score = 0.35 * passage.score + 0.65 * rr_norm
                rescored.append(
                    Passage(
                        chunk_id=passage.chunk_id,
                        text=passage.text,
                        source_path=passage.source_path,
                        section=passage.section,
                        doc_type=passage.doc_type,
                        sprint_id=passage.sprint_id,
                        anchor=passage.anchor,
                        score=score,
                        dataset_version=passage.dataset_version,
                        region=passage.region,
                        scope=passage.scope,
                        data_source=passage.data_source,
                    )
                )
            rescored.sort(key=lambda p: p.score, reverse=True)
            return rescored
        except Exception:
            return passages

    def _load_reranker(self):
        if self._reranker is False:
            return None
        if self._reranker is not None:
            return self._reranker
        try:
            from sentence_transformers import CrossEncoder

            self._reranker = CrossEncoder(self.config.rerank_model)
            return self._reranker
        except Exception:
            self._reranker = False
            return None

    def top_passages(
        self,
        query: str,
        *,
        top_n: int | None = None,
        doc_types: list[str] | None = None,
        dataset_version: str | None = None,
        region: Literal["CE", "SP", "CE+SP"] | None = None,
    ) -> list[Passage]:
        top = top_n or self.config.rerank_top_n
        return self.retrieve(
            query,
            k=self.config.retrieval_k,
            doc_types=doc_types,
            dataset_version=dataset_version,
            region=region,
        )[:top]

    def get_by_anchors(
        self,
        anchors: list[str],
        *,
        dataset_version: str | None = None,
    ) -> list[Passage]:
        """Busca determinística por anchor — usado para forçar inclusão de cards
        canônicos no contexto quando a intenção da query é claramente identificável.

        Retorna no máximo 1 passage por anchor (o mais recente se houver duplicatas
        por versão de dataset).
        """
        if not anchors:
            return []
        self._ensure_ready()
        where_clauses: list[dict[str, object]] = [
            {"anchor": {"$in": list(anchors)}},
            {"doc_type": "data"},
        ]
        if dataset_version:
            where_clauses.append({"dataset_version": dataset_version})
        where = where_clauses[0] if len(where_clauses) == 1 else {"$and": where_clauses}
        result = self._collection.get(where=where, limit=max(len(anchors) * 4, 16))  # type: ignore[union-attr]
        ids = result.get("ids", []) or []
        docs = result.get("documents", []) or []
        metas = result.get("metadatas", []) or []
        by_anchor: dict[str, Passage] = {}
        for cid, text, meta in zip(ids, docs, metas, strict=False):
            m = meta or {}
            anchor = str(m.get("anchor", ""))
            if anchor and anchor not in by_anchor:
                by_anchor[anchor] = Passage(
                    chunk_id=cid,
                    text=text,
                    source_path=str(m.get("source_path", "")),
                    section=str(m.get("section", "")),
                    doc_type=str(m.get("doc_type", "data")),
                    sprint_id=str(m.get("sprint_id", "")),
                    anchor=anchor,
                    score=0.99,  # score sintético alto — card canônico para a intenção
                    dataset_version=str(m.get("dataset_version", "")),
                    region=str(m.get("region", "CE+SP")),
                    scope=str(m.get("scope", "regional")),
                    data_source=str(m.get("data_source", "silver.erro_leitura_normalizado")),
                )
        # Preserva a ordem de prioridade passada pelo caller
        return [by_anchor[a] for a in anchors if a in by_anchor]


def route_doc_types(query: str) -> list[str] | None:
    """Heurística de roteamento: reduz o espaço de busca por palavra-chave.

    Objetivo: enviar menos chunks ao LLM quando a intenção é clara.
    """
    q = query.lower()
    if re.search(r"(ceará|cearense|fortaleza|\bce\b)", q):
        return ["data", "business", "viz"]
    if re.search(r"(são paulo|paulista|\bsp\b)", q):
        return ["data", "business", "viz"]
    analytics_terms = (
        "quantos", "quantas", "volume", "total de", "percentual", "porcentagem",
        "top ", "ranking", "maior", "mais frequente", "evolução", "mensal",
        "reclamações", "reclamacoes", "causa-raiz", "causa raiz", "assunto",
        "reincid", "sazon", "perfil", "medidor", "fatura", "taxonomia",
    )
    if any(term in q for term in analytics_terms):
        return ["data", "business", "viz"]
    if any(term in q for term in ("sprint", "entregável", "deliverable")):
        return ["sprint"]
    if any(term in q for term in ("acf", "asf")):
        return ["business", "viz"]
    if any(term in q for term in ("refatur", "religa", "grupo b", "grupo a", "gd ")):
        return ["data", "business", "viz"]
    if any(
        term in q
        for term in ("modelo", "predict", "feature", "isolation", "lightgbm", "xgboost")
    ):
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


def _expand_query(query: str) -> str:
    q = query.strip()
    low = q.lower()
    extras: list[str] = []
    for trigger, synonyms in _QUERY_EXPANSION_HINTS:
        if trigger in low:
            extras.extend(synonyms)
    if not extras:
        return q
    # Append-only expansion to preserve original semantics.
    return f"{q} {' '.join(extras)}"


def _intent_anchor_bonus(query: str, anchor: str) -> float:
    q = query.lower()
    a = str(anchor).lower()
    bonus = 0.0
    if "instala" in q and "instal" in a:
        bonus += 0.08
    if ("assunto" in q or "tema" in q) and "assunto" in a:
        bonus += 0.06
    if ("causa" in q or "motivo" in q) and ("causa" in a or "observacoes" in a):
        bonus += 0.06
    if ("sazon" in q or "mensal" in q) and ("mensal" in a or "sazon" in a):
        bonus += 0.05
    if "reincid" in q and "reincid" in a:
        bonus += 0.06
    if ("medidor" in q or "fatura" in q or "perfil" in q) and "perfil" in a:
        bonus += 0.06
    return bonus


def _region_anchor_bonus(
    region: Literal["CE", "SP", "CE+SP"] | None,
    anchor: str,
) -> float:
    a = str(anchor).lower()
    if not a:
        return 0.0
    if region == "SP" and a.startswith("sp-"):
        return 0.06
    if region == "CE" and a.startswith("ce-"):
        return 0.06
    if region == "CE+SP" and (
        a.startswith("ce-vs-sp-")
        or a in {"instalacoes-por-regional", "sazonalidade-ce-sp", "motivos-taxonomia-ce-sp"}
    ):
        return 0.05
    return 0.0


def _query_structure_bonus(query: str, anchor: str) -> float:
    q = query.lower()
    a = str(anchor).lower()
    bonus = 0.0
    if "refaturamento produtos" in q and "ce-reclamacoes-totais" in a:
        bonus += 0.07
    if (
        any(term in q for term in ("motivo", "motivos", "causa", "causas"))
        and "medidor" in q
        and "sp-causas-por-tipo-medidor" in a
    ):
        bonus += 0.08
    if any(term in q for term in ("taxonomia", "motivo consolidado")) and "motivos-taxonomia" in a:
        bonus += 0.06
    return bonus
