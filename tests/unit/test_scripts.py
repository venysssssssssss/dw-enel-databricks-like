from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

from scripts.bootstrap_sql import main as bootstrap_sql_main
from scripts.rag_prepare_training_data import build_triplets, load_feedback, load_telemetry
from scripts.seed_dim_tempo import build_rows
from scripts.train_embedding_cpu import load_triplets
from src.common.sample_data import generate_sample_files

if TYPE_CHECKING:
    from pathlib import Path


def test_generate_sample_files(tmp_path: Path) -> None:
    files = generate_sample_files(rows=20, output_dir=tmp_path)
    assert any(file.name == "notas_operacionais.csv" for file in files)
    assert all(file.exists() for file in files)


def test_seed_dim_tempo_rows_cover_ufs() -> None:
    rows = build_rows(date(2026, 1, 1), date(2026, 1, 2))
    assert {row["uf"] for row in rows} == {"SP", "RJ", "CE", "GO"}
    assert all("flag_dia_util" in row for row in rows)


def test_bootstrap_sql_command_writes_files(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr("sys.argv", ["bootstrap_sql.py", "--output-dir", str(tmp_path)])
    result = bootstrap_sql_main()
    assert result == 0
    assert (tmp_path / "bronze_notas_operacionais.sql").exists()


def test_rag_prepare_training_data_builds_weighted_triplets(tmp_path: Path) -> None:
    telemetry_path = tmp_path / "telemetry.jsonl"
    feedback_path = tmp_path / "feedback.csv"
    telemetry_path.write_text(
        "\n".join(
            [
                '{"question_hash":"h1","question_preview":"Q1",'
                '"extra":{"sources":["docs/a.md#a1"]},"cache_hit":true}',
                '{"question_hash":"h2","question_preview":"Q2",'
                '"extra":{"sources":["docs/a.md#a2"]}}',
            ]
        ),
        encoding="utf-8",
    )
    feedback_path.write_text("question_hash,rating\nh2,down\n", encoding="utf-8")

    triplets = build_triplets(
        telemetry=load_telemetry(telemetry_path),
        feedback=load_feedback(feedback_path),
        anchor_to_text={"a1": "positivo 1", "a2": "negativo 2", "a3": "alternativo 3"},
    )

    assert len(triplets) == 2
    assert {triplet["weight"] for triplet in triplets} == {1.0}
    assert triplets[1]["negative"] == "negativo 2"


def test_train_embedding_load_triplets_uses_fallback_for_missing_file(tmp_path: Path) -> None:
    class DummyInputExample:
        def __init__(self, *, texts: list[str], label: float | None = None) -> None:
            self.texts = texts
            self.label = label

    examples = load_triplets(tmp_path / "missing.jsonl", DummyInputExample)

    assert len(examples) == 2
    assert examples[0].texts[0] == "O que é ACF?"
