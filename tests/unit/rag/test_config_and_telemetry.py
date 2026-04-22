from __future__ import annotations

import json
from typing import TYPE_CHECKING
from unittest.mock import patch

from src.rag.config import load_rag_config
from src.rag.telemetry import TurnTelemetry, hash_question, log_feedback, preview, record

if TYPE_CHECKING:
    from pathlib import Path


def test_load_rag_config_defaults(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("ENEL_PROJECT_ROOT", str(tmp_path))
    (tmp_path / "docs").mkdir()
    cfg = load_rag_config()
    assert cfg.provider in {"llama_cpp", "stub", "openai", "anthropic", "ollama"}
    assert cfg.chunk_size_tokens > 0
    assert cfg.retrieval_k >= cfg.rerank_top_n
    assert cfg.similarity_threshold >= 0.0
    assert cfg.regional_scope == "CE+SP"
    assert cfg.prompt_version == "2.0.0"


def test_load_rag_config_env_overrides(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("ENEL_PROJECT_ROOT", str(tmp_path))
    monkeypatch.setenv("RAG_PROVIDER", "stub")
    monkeypatch.setenv("RAG_MAX_TURN_TOKENS", "4096")
    monkeypatch.setenv("RAG_CHUNK_SIZE", "256")
    monkeypatch.setenv("RAG_SIMILARITY_THRESHOLD", "0.4")
    monkeypatch.setenv("RAG_REGIONAL_SCOPE", "SP")
    monkeypatch.setenv("RAG_PROMPT_VERSION", "1.0.0")
    cfg = load_rag_config()
    assert cfg.provider == "stub"
    assert cfg.max_turn_tokens == 4096
    assert cfg.chunk_size_tokens == 256
    assert cfg.similarity_threshold == 0.4
    assert cfg.regional_scope == "SP"
    assert cfg.prompt_version == "1.0.0"


def test_hash_question_stable() -> None:
    a = hash_question("O que é ACF?")
    b = hash_question("O que é ACF?")
    assert a == b
    assert len(a) == 16


def test_preview_truncates_and_single_line() -> None:
    assert preview("linha 1\nlinha 2", n=80) == "linha 1 linha 2"
    assert len(preview("x" * 200, n=80)) == 80


def test_record_appends_jsonl(tmp_path: Path) -> None:
    path = tmp_path / "telemetry.jsonl"
    turn = TurnTelemetry(
        ts="2026-04-15T00:00:00Z",
        provider="stub",
        model="stub",
        question_hash="abc",
        question_preview="o que",
        intent_class="glossario",
        n_passages=2,
        prompt_tokens=100,
        completion_tokens=50,
        cache_hit=False,
        latency_first_token_ms=500,
        latency_total_ms=1200,
    )
    record(path, turn)
    record(path, turn)
    lines = path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
    parsed = json.loads(lines[0])
    assert parsed["provider"] == "stub"
    assert parsed["n_passages"] == 2


def test_log_feedback_writes_header_once(tmp_path: Path) -> None:
    path = tmp_path / "feedback.csv"
    assert log_feedback(path, question_hash="abc", rating="up", comment="muito bom")
    assert log_feedback(path, question_hash="def", rating="down", comment="imprec, iso\nlinha nova")
    assert not log_feedback(path, question_hash="ghi", rating="INVALID")
    content = path.read_text(encoding="utf-8").splitlines()
    assert content[0] == "timestamp,question_hash,rating,comment"
    assert len(content) == 3  # header + 2 válidos
    assert "muito bom" in content[1]
    # garante que não quebra CSV (vírgula vira ponto-e-vírgula, \n vira espaço)
    assert "\n" not in content[2].split(",", 3)[-1]


def test_log_feedback_returns_false_when_file_is_not_writable(tmp_path: Path) -> None:
    path = tmp_path / "feedback.csv"
    with patch.object(type(path), "open", side_effect=PermissionError("denied")):
        assert not log_feedback(path, question_hash="abc", rating="up")
