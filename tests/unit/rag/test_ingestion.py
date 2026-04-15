from __future__ import annotations

from pathlib import Path

import pytest

from src.rag.ingestion import chunk_markdown, discover_files


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
