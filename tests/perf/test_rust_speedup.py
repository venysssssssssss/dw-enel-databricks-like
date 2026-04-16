from __future__ import annotations

from src.rag.ingestion import _load_embedder
from src.rag.retriever import lexical_overlap


def test_rust_hot_path_fallback_contracts_are_stable() -> None:
    embed = _load_embedder("hashing")
    vector = embed(["erro leitura refaturamento"])[0]

    assert len(vector) == 256
    assert any(value != 0 for value in vector)
    assert lexical_overlap("erro leitura", "erro de leitura com refaturamento") > 0
