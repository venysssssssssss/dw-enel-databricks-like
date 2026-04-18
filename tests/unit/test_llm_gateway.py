from __future__ import annotations

from typing import Any

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
