from __future__ import annotations

import threading
import time
from typing import Any

import pytest

from src.common.llm_gateway import LlamaCppProvider


class _FakeLlama:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def create_chat_completion(self, **kwargs):  # noqa: ANN003
        self.calls.append(kwargs)
        max_tokens = int(kwargs.get("max_tokens", 0))
        if len(self.calls) == 1:
            raise ValueError(
                "Requested tokens (4120) exceed context window of 4096"
            )
        if kwargs.get("stream"):
            return [
                {"choices": [{"delta": {"content": "ok"}}]},
                {"choices": [{"delta": {"content": "!"}}]},
            ]
        return {
            "choices": [{"message": {"content": "resposta"}}],
            "usage": {"prompt_tokens": 120, "completion_tokens": max_tokens},
        }


def _provider_with_fake_llama(fake: _FakeLlama) -> LlamaCppProvider:
    provider = object.__new__(LlamaCppProvider)
    provider.model = "fake.gguf"
    provider._llama = fake
    return provider


class _BlockingLlama:
    def __init__(self, started: threading.Event, release: threading.Event) -> None:
        self.started = started
        self.release = release

    def create_chat_completion(self, **kwargs):  # noqa: ANN003
        self.started.set()
        self.release.wait(timeout=2.0)
        return {
            "choices": [{"message": {"content": "done"}}],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1},
        }


def test_complete_retries_with_lower_max_tokens_on_context_overflow() -> None:
    fake = _FakeLlama()
    provider = _provider_with_fake_llama(fake)
    response = provider.complete(  # type: ignore[misc]
        [{"role": "user", "content": "pergunta"}],
        max_tokens=400,
    )
    assert response.text == "resposta"
    assert len(fake.calls) == 2
    assert int(fake.calls[0]["max_tokens"]) == 400
    assert int(fake.calls[1]["max_tokens"]) < 400
    assert int(fake.calls[1]["max_tokens"]) >= 16


def test_stream_retries_with_lower_max_tokens_on_context_overflow() -> None:
    fake = _FakeLlama()
    provider = _provider_with_fake_llama(fake)
    chunks = list(
        provider.stream(  # type: ignore[misc]
            [{"role": "user", "content": "pergunta"}],
            max_tokens=300,
        )
    )
    assert chunks == ["ok", "!"]
    assert len(fake.calls) == 2
    assert int(fake.calls[0]["max_tokens"]) == 300
    assert int(fake.calls[1]["max_tokens"]) < 300


def test_complete_rejects_when_generation_queue_is_full() -> None:
    from src.common.llm_gateway import _GenerationGate

    started = threading.Event()
    release = threading.Event()
    provider = object.__new__(LlamaCppProvider)
    provider.model = "fake.gguf"
    provider._llama = _BlockingLlama(started, release)
    provider._gate = _GenerationGate(max_active=1, queue_size=0, wait_timeout_sec=0.2)

    errors: list[Exception] = []

    def worker() -> None:
        provider.complete([{"role": "user", "content": "primeira"}])  # type: ignore[misc]

    thread = threading.Thread(target=worker)
    thread.start()
    assert started.wait(timeout=1.0)

    try:
        with pytest.raises(RuntimeError, match="queue is full"):
            provider.complete([{"role": "user", "content": "segunda"}])  # type: ignore[misc]
    finally:
        release.set()
        thread.join(timeout=1.0)
    assert not errors


def test_stream_releases_generation_gate_when_closed_early() -> None:
    from src.common.llm_gateway import _GenerationGate

    class _StreamingLlama:
        def create_chat_completion(self, **kwargs):  # noqa: ANN003
            if kwargs.get("stream"):
                def _iter():
                    yield {"choices": [{"delta": {"content": "a"}}]}
                    time.sleep(0.01)
                    yield {"choices": [{"delta": {"content": "b"}}]}

                return _iter()
            return {
                "choices": [{"message": {"content": "ok"}}],
                "usage": {"prompt_tokens": 1, "completion_tokens": 1},
            }

    provider = object.__new__(LlamaCppProvider)
    provider.model = "fake.gguf"
    provider._llama = _StreamingLlama()
    provider._gate = _GenerationGate(max_active=1, queue_size=0, wait_timeout_sec=0.2)

    stream = provider.stream([{"role": "user", "content": "pergunta"}])  # type: ignore[misc]
    assert next(stream) == "a"
    stream.close()

    response = provider.complete([{"role": "user", "content": "nova"}])  # type: ignore[misc]
    assert response.text == "ok"
