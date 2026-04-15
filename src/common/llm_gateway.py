"""Gateway multi-provider para LLMs.

Default: `llama_cpp` (open-source, CPU-only, GGUF quantizado).
Fallback: `stub` (sem LLM) — responde com contexto recuperado formatado.
Opcionais: `openai`, `anthropic`, `ollama` (se chaves/serviços estiverem configurados).

A interface é deliberadamente simples: `complete(messages, stream)` — evita
lock-in e mantém todo o código RAG agnóstico de provider.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

Message = dict[str, str]


@dataclass(frozen=True, slots=True)
class LLMResponse:
    text: str
    prompt_tokens: int
    completion_tokens: int
    provider: str
    model: str
    cache_hit: bool = False


class LLMProvider(Protocol):
    name: str
    model: str

    def complete(
        self,
        messages: list[Message],
        *,
        max_tokens: int = 512,
        temperature: float = 0.2,
        top_p: float = 0.9,
        stop: list[str] | None = None,
    ) -> LLMResponse: ...

    def stream(
        self,
        messages: list[Message],
        *,
        max_tokens: int = 512,
        temperature: float = 0.2,
        top_p: float = 0.9,
        stop: list[str] | None = None,
    ) -> Iterator[str]: ...


class StubProvider:
    """Provider que não chama LLM — usado em testes e como fallback sem deps.

    Retorna a última mensagem `user` concatenada com o contexto do sistema,
    preservando citações. Util para rodar a pipeline sem GPU, sem GGUF baixado,
    sem API — ideal para CI.
    """

    name = "stub"
    model = "stub-echo"

    def complete(
        self,
        messages: list[Message],
        *,
        max_tokens: int = 512,
        temperature: float = 0.2,
        top_p: float = 0.9,
        stop: list[str] | None = None,
    ) -> LLMResponse:
        del max_tokens, temperature, top_p, stop
        text = _stub_answer(messages)
        return LLMResponse(
            text=text,
            prompt_tokens=sum(len(m.get("content", "")) // 4 for m in messages),
            completion_tokens=len(text) // 4,
            provider=self.name,
            model=self.model,
        )

    def stream(
        self,
        messages: list[Message],
        *,
        max_tokens: int = 512,
        temperature: float = 0.2,
        top_p: float = 0.9,
        stop: list[str] | None = None,
    ) -> Iterator[str]:
        resp = self.complete(
            messages,
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
            stop=stop,
        )
        yield resp.text


def _stub_answer(messages: list[Message]) -> str:
    user_q = next(
        (m["content"] for m in reversed(messages) if m.get("role") == "user"),
        "",
    )
    system_ctx = next(
        (m["content"] for m in messages if m.get("role") == "system"),
        "",
    )
    citations = [line for line in system_ctx.splitlines() if line.startswith("[fonte:")]
    cite_block = "\n".join(citations[:3]) if citations else ""
    return (
        "Resposta baseada nos documentos recuperados (modo stub, sem LLM ativo).\n\n"
        f"Pergunta recebida: {user_q[:200]}\n\n"
        "Para gerar respostas naturais, configure `RAG_PROVIDER=llama_cpp` e baixe o modelo com "
        "`scripts/build_rag_corpus.py --download-model`.\n\n"
        f"{cite_block}"
    ).strip()


class LlamaCppProvider:
    """LLM local via `llama-cpp-python` com modelo GGUF quantizado.

    Recomendado: Qwen2.5-3B-Instruct Q4_K_M (~2GB RAM), licença Apache 2.0.
    First-token típico em CPU i7 ~1-3s; throughput ~8-15 tok/s.
    """

    name = "llama_cpp"

    def __init__(
        self,
        *,
        model_path: Path,
        n_ctx: int = 4096,
        n_threads: int = 4,
        chat_format: str | None = None,
    ) -> None:
        try:
            from llama_cpp import Llama
        except ImportError as exc:
            raise RuntimeError(
                "llama-cpp-python não instalado. Rode: "
                "pip install -e '.[rag]' ou pip install llama-cpp-python"
            ) from exc

        if not model_path.exists():
            raise FileNotFoundError(
                f"Modelo GGUF não encontrado em {model_path}. "
                "Baixe via scripts/build_rag_corpus.py --download-model."
            )

        self.model = model_path.name
        self._llama = Llama(
            model_path=str(model_path),
            n_ctx=n_ctx,
            n_threads=n_threads,
            chat_format=chat_format,
            verbose=False,
            logits_all=False,
        )

    def complete(
        self,
        messages: list[Message],
        *,
        max_tokens: int = 512,
        temperature: float = 0.2,
        top_p: float = 0.9,
        stop: list[str] | None = None,
    ) -> LLMResponse:
        out = self._llama.create_chat_completion(
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
            stop=stop or [],
            stream=False,
        )
        text = out["choices"][0]["message"]["content"]
        usage = out.get("usage", {})
        return LLMResponse(
            text=text,
            prompt_tokens=int(usage.get("prompt_tokens", 0)),
            completion_tokens=int(usage.get("completion_tokens", 0)),
            provider=self.name,
            model=self.model,
        )

    def stream(
        self,
        messages: list[Message],
        *,
        max_tokens: int = 512,
        temperature: float = 0.2,
        top_p: float = 0.9,
        stop: list[str] | None = None,
    ) -> Iterator[str]:
        it = self._llama.create_chat_completion(
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
            stop=stop or [],
            stream=True,
        )
        for chunk in it:
            delta = chunk["choices"][0]["delta"].get("content", "")
            if delta:
                yield delta


class OllamaProvider:
    """Provider Ollama via HTTP (para quem já roda Ollama localmente)."""

    name = "ollama"

    def __init__(self, *, model: str, host: str = "http://localhost:11434") -> None:
        self.model = model
        self.host = host.rstrip("/")

    def complete(
        self,
        messages: list[Message],
        *,
        max_tokens: int = 512,
        temperature: float = 0.2,
        top_p: float = 0.9,
        stop: list[str] | None = None,
    ) -> LLMResponse:
        import httpx

        body: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {"num_predict": max_tokens, "temperature": temperature, "top_p": top_p},
        }
        if stop:
            body["options"]["stop"] = stop
        r = httpx.post(f"{self.host}/api/chat", json=body, timeout=120)
        r.raise_for_status()
        data = r.json()
        text = data.get("message", {}).get("content", "")
        return LLMResponse(
            text=text,
            prompt_tokens=int(data.get("prompt_eval_count", 0)),
            completion_tokens=int(data.get("eval_count", 0)),
            provider=self.name,
            model=self.model,
        )

    def stream(
        self,
        messages: list[Message],
        *,
        max_tokens: int = 512,
        temperature: float = 0.2,
        top_p: float = 0.9,
        stop: list[str] | None = None,
    ) -> Iterator[str]:
        import httpx

        body: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": True,
            "options": {"num_predict": max_tokens, "temperature": temperature, "top_p": top_p},
        }
        if stop:
            body["options"]["stop"] = stop
        with httpx.stream("POST", f"{self.host}/api/chat", json=body, timeout=120) as r:
            r.raise_for_status()
            for line in r.iter_lines():
                if not line:
                    continue
                try:
                    data = json.loads(line)
                except json.JSONDecodeError:
                    continue
                chunk = data.get("message", {}).get("content", "")
                if chunk:
                    yield chunk
                if data.get("done"):
                    break


def build_provider(config: Any) -> LLMProvider:
    """Factory que escolhe provider a partir de `RagConfig`.

    Ordem de preferência e comportamento sem deps/modelo: cai para `StubProvider`,
    permitindo rodar a pipeline toda sem LLM em CI e em ambientes de dev sem GPU.
    """

    provider = getattr(config, "provider", "stub").lower()

    if provider == "stub":
        return StubProvider()

    if provider == "llama_cpp":
        try:
            model_path = _resolve_model_path(config)
            return LlamaCppProvider(
                model_path=model_path,
                n_ctx=config.n_ctx,
                n_threads=config.n_threads,
            )
        except (RuntimeError, FileNotFoundError):
            return StubProvider()

    if provider == "ollama":
        try:
            return OllamaProvider(model=config.model_file or "qwen2.5:3b")
        except Exception:
            return StubProvider()

    return StubProvider()


def _resolve_model_path(config: Any) -> Path:
    if config.model_path and config.model_path.exists():
        return config.model_path
    default = Path("data/rag/models") / config.model_file
    if default.exists():
        return default
    raise FileNotFoundError(
        f"Nenhum GGUF encontrado em {config.model_path} nem em {default}. "
        "Rode: python scripts/build_rag_corpus.py --download-model"
    )
