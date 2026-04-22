from __future__ import annotations

import sys
import types
from typing import TYPE_CHECKING

import pytest

from src.rag.ingestion import _load_embedder, chunk_markdown, discover_files

if TYPE_CHECKING:
    from pathlib import Path


def test_discover_files_finds_markdown(tmp_path: Path) -> None:
    (tmp_path / "a.md").write_text("# A", encoding="utf-8")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "b.md").write_text("# B", encoding="utf-8")
    (tmp_path / "ignore.txt").write_text("x", encoding="utf-8")
    files = discover_files([tmp_path])
    names = {f.name for f in files}
    assert names == {"a.md", "b.md"}


def test_chunk_markdown_respects_headers(tmp_path: Path) -> None:
    content = (
        "# Intro\n\nPrimeiro parágrafo com conteúdo relevante para indexar no corpus.\n\n"
        "## Seção A\n\nTexto da seção A explicando regras de negócio do ENEL.\n\n"
        "## Seção B\n\nTexto da seção B com mais detalhes importantes e exemplos.\n"
    )
    p = tmp_path / "docs" / "business-rules" / "doc.md"
    p.parent.mkdir(parents=True)
    p.write_text(content, encoding="utf-8")
    chunks = chunk_markdown(
        path=p,
        content=content,
        chunk_size_tokens=120,
        overlap_tokens=16,
        project_root=tmp_path,
    )
    assert len(chunks) >= 3
    sections = {c.section for c in chunks}
    assert "Intro" in sections
    assert any("Seção A" in s for s in sections)
    assert all(c.doc_type == "business" for c in chunks)
    assert all(c.source_path.endswith("doc.md") for c in chunks)


def test_chunk_markdown_splits_long_blocks(tmp_path: Path) -> None:
    content = "# Título\n\n" + ("palavra " * 800) + "\n"
    p = tmp_path / "long.md"
    p.write_text(content, encoding="utf-8")
    chunks = chunk_markdown(
        path=p,
        content=content,
        chunk_size_tokens=100,
        overlap_tokens=10,
        project_root=tmp_path,
    )
    assert len(chunks) > 1
    assert all(c.token_count <= 200 for c in chunks)


def test_chunk_markdown_skips_tiny_pieces(tmp_path: Path) -> None:
    p = tmp_path / "tiny.md"
    p.write_text("# X\n\nshort", encoding="utf-8")
    chunks = chunk_markdown(
        path=p,
        content="# X\n\nshort",
        chunk_size_tokens=500,
        overlap_tokens=50,
        project_root=tmp_path,
    )
    assert chunks == []


@pytest.mark.parametrize(
    "filename,expected_type",
    [
        ("docs/business-rules/foo.md", "business"),
        ("docs/sprints/sprint-13.md", "sprint"),
        ("docs/ml/models.md", "ml"),
        ("docs/api/endpoints.md", "api"),
        ("docs/architecture/data-flow.md", "architecture"),
        ("README.md", "root"),
    ],
)
def test_doc_type_inference(tmp_path: Path, filename: str, expected_type: str) -> None:
    p = tmp_path / filename
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("# H\n\ncorpo suficientemente longo para virar chunk indexado.", encoding="utf-8")
    chunks = chunk_markdown(
        path=p,
        content=p.read_text(encoding="utf-8"),
        chunk_size_tokens=200,
        overlap_tokens=20,
        project_root=tmp_path,
    )
    assert chunks
    assert chunks[0].doc_type == expected_type


def test_hashing_embedder_is_stateless_and_fixed_dimension() -> None:
    embed = _load_embedder("hashing")
    batch_vector = embed(["erro leitura refaturamento", "dashboard sprint rag"])[0]
    single_vector = embed(["erro leitura refaturamento"])[0]
    assert len(batch_vector) == 256
    assert len(single_vector) == 256
    assert single_vector == batch_vector
    assert any(value != 0 for value in single_vector)


def test_load_embedder_uses_rust_onnx_when_model_path_mentions_onnx(monkeypatch) -> None:
    class FakeOnnxEmbedder:
        def __init__(self, model_path: str) -> None:
            self.model_path = model_path

        def embed(self, texts: list[str]) -> list[list[float]]:
            return [[float(len(text)), 1.0] for text in texts]

    fake_module = types.SimpleNamespace(OnnxEmbedder=FakeOnnxEmbedder)
    monkeypatch.setitem(sys.modules, "enel_core", fake_module)

    embed = _load_embedder("/models/enel-minilm-onnx")

    assert embed(["abc", "de"]) == [[3.0, 1.0], [2.0, 1.0]]


def test_load_embedder_requires_onnx_when_strict_mode_is_enabled(monkeypatch) -> None:
    class FailingOnnxEmbedder:
        def __init__(self, model_path: str) -> None:
            raise FileNotFoundError(model_path)

    fake_module = types.SimpleNamespace(OnnxEmbedder=FailingOnnxEmbedder)
    monkeypatch.setitem(sys.modules, "enel_core", fake_module)
    monkeypatch.setenv("RAG_REQUIRE_ONNX_EMBEDDING", "1")

    with pytest.raises(RuntimeError, match="RAG_REQUIRE_ONNX_EMBEDDING=1"):
        _load_embedder("/models/enel-minilm-onnx")
