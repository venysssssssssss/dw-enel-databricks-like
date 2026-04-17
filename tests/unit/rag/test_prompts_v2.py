from __future__ import annotations

import importlib


def test_prompt_v2_default(monkeypatch) -> None:
    monkeypatch.delenv("RAG_PROMPT_VERSION", raising=False)
    prompts = importlib.import_module("src.rag.prompts")
    prompts = importlib.reload(prompts)
    assert prompts.PROMPT_VERSION == "2.0.0"
    assert "ESCOPO REGIONAL" in prompts.SYSTEM_STATIC
    assert "REGRAS DE EXATIDÃO DE RESPOSTA" in prompts.SYSTEM_STATIC
    assert "CAVEATS DE QUALIDADE DE DADOS" in prompts.SYSTEM_STATIC


def test_prompt_v1_rollback(monkeypatch) -> None:
    monkeypatch.setenv("RAG_PROMPT_VERSION", "1.0.0")
    prompts = importlib.import_module("src.rag.prompts")
    prompts = importlib.reload(prompts)
    assert prompts.PROMPT_VERSION == "1.0.0"
    assert "ESCOPO REGIONAL" not in prompts.SYSTEM_STATIC
    assert "REGRAS DE RESPOSTA" in prompts.SYSTEM_STATIC
