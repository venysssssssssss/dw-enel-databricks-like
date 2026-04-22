"""Benchmark API RAG responses with PyTorch vs ONNX embeddings.

The script exercises the real FastAPI `/v1/rag/stream` route through TestClient,
using isolated ChromaDB directories for each embedding backend.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import src.rag.orchestrator as orchestrator_module  # noqa: E402
from src.api.main import create_app  # noqa: E402
from src.rag.config import RagConfig, load_rag_config  # noqa: E402
from src.rag.eval.metrics import answer_exactness, citation_accuracy  # noqa: E402
from src.rag.ingestion import build_corpus  # noqa: E402
from src.rag.orchestrator import RagOrchestrator  # noqa: E402

DEFAULT_CASE_IDS = (
    "s18-001",
    "s18-002",
    "s18-003",
    "s18-004",
    "s18-005",
    "s18-006",
    "s18-007",
    "s18-008",
    "s18-009",
    "s18-010",
    "s18-011",
    "s18-012",
    "s18-013",
    "s18-014",
    "s18-015",
    "s18-016",
    "s18-017",
    "s18-018",
    "s18-019",
    "cmp-001",
    "cmp-002",
    "cmp-003",
    "cmp-004",
    "cmp-005",
    "cmp-006",
    "cmp-007",
    "cmp-008",
    "cmp-009",
    "cmp-010",
    "sp-001",
)


@dataclass(frozen=True, slots=True)
class BenchCase:
    id: str
    question: str
    expected_sources: list[str]
    expected_keywords: list[str]
    forbidden_keywords: list[str]
    answer_must_refuse: bool


@dataclass(frozen=True, slots=True)
class BenchResult:
    backend: str
    case_id: str
    question: str
    status_code: int
    latency_ms_client: float
    latency_ms_api: float | None
    cache_hit: bool | None
    answer_chars: int
    citation_accuracy: float
    answer_exactness: float
    error: str | None
    answer_preview: str


def load_cases(path: Path, case_ids: tuple[str, ...]) -> list[BenchCase]:
    wanted = set(case_ids)
    cases: list[BenchCase] = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            raw = json.loads(line)
            if raw["id"] not in wanted:
                continue
            cases.append(
                BenchCase(
                    id=str(raw["id"]),
                    question=str(raw["question"]),
                    expected_sources=list(raw.get("expected_sources") or []),
                    expected_keywords=list(raw.get("expected_keywords") or []),
                    forbidden_keywords=list(raw.get("forbidden_keywords") or []),
                    answer_must_refuse=bool(raw.get("answer_must_refuse")),
                )
            )
    index = {case.id: case for case in cases}
    missing = [case_id for case_id in case_ids if case_id not in index]
    if missing:
        raise ValueError(f"Casos não encontrados no golden set: {missing}")
    return [index[case_id] for case_id in case_ids]


def benchmark_backend(
    *,
    backend: str,
    config: RagConfig,
    cases: list[BenchCase],
    rebuild: bool,
    disable_known_cache: bool,
) -> list[BenchResult]:
    if rebuild:
        build_started = time.perf_counter()
        print(f"[bench] {backend}: build_corpus rebuild=True", flush=True)
        stats = build_corpus(config, rebuild=True)
        build_elapsed = time.perf_counter() - build_started
        print(
            f"[bench] {backend}: corpus chunks={stats.chunks_created} "
            f"tokens={stats.tokens_indexed} skipped={len(stats.skipped)} "
            f"elapsed={build_elapsed:.1f}s",
            flush=True,
        )
        if stats.chunks_created == 0:
            raise RuntimeError(f"Corpus vazio para backend {backend}: {stats.as_dict()}")
    else:
        sqlite_path = config.chromadb_path / "chroma.sqlite3"
        if not sqlite_path.exists():
            raise FileNotFoundError(
                f"Índice {backend} não existe em {config.chromadb_path}; rode com rebuild."
            )
        print(f"[bench] {backend}: using existing index {config.chromadb_path}", flush=True)

    print(f"[bench] {backend}: create_app/TestClient", flush=True)
    app = create_app(
        enable_lifespan=False,
        enable_rate_limit=False,
        enable_observability=False,
        enable_middlewares=False,
    )
    app.state.rag_config = config
    if disable_known_cache:
        orchestrator_module.resolve_known_answer = _disabled_known_answer
    app.state.rag_orchestrator = RagOrchestrator(config)

    results: list[BenchResult] = []
    with TestClient(app) as client:
        for index, case in enumerate(cases, start=1):
            print(f"[bench] {backend}: request {index:02d}/{len(cases)} {case.id}", flush=True)
            started = time.perf_counter()
            response = client.post("/v1/rag/stream", json={"question": case.question})
            elapsed_ms = (time.perf_counter() - started) * 1000
            text, done, error = parse_sse(response.text)
            if response.status_code != 200 and error is None:
                error = response.text[:500]
            if error is None and not text:
                error = "Resposta vazia"
            results.append(
                BenchResult(
                    backend=backend,
                    case_id=case.id,
                    question=case.question,
                    status_code=response.status_code,
                    latency_ms_client=round(elapsed_ms, 3),
                    latency_ms_api=done.get("latency_ms") if done else None,
                    cache_hit=done.get("cache_hit") if done else None,
                    answer_chars=len(text),
                    citation_accuracy=round(
                        citation_accuracy(text, case.expected_sources),
                        4,
                    ),
                    answer_exactness=round(
                        answer_exactness(
                            text,
                            case.expected_keywords,
                            case.forbidden_keywords,
                        ),
                        4,
                    ),
                    error=error,
                    answer_preview=" ".join(text.split())[:300],
                )
            )
    return results


def parse_sse(raw: str) -> tuple[str, dict[str, Any], str | None]:
    tokens: list[str] = []
    done: dict[str, Any] = {}
    error: str | None = None
    current_event: str | None = None
    current_data: str | None = None
    for line in raw.splitlines():
        if line.startswith("event:"):
            current_event = line.removeprefix("event:").strip()
        elif line.startswith("data:"):
            current_data = line.removeprefix("data:").strip()
        elif not line.strip() and current_event and current_data is not None:
            payload = json.loads(current_data)
            if current_event == "token":
                tokens.append(str(payload.get("text") or ""))
            elif current_event == "done":
                done = payload
            elif current_event == "error":
                error = str(payload.get("message") or payload)
            current_event = None
            current_data = None
    return "".join(tokens), done, error


def _disabled_known_answer(*args: object, **kwargs: object) -> None:
    del args, kwargs
    return None


def summarize(results: list[BenchResult]) -> dict[str, Any]:
    by_backend: dict[str, list[BenchResult]] = {}
    for result in results:
        by_backend.setdefault(result.backend, []).append(result)

    summary: dict[str, Any] = {}
    for backend, rows in by_backend.items():
        latencies = [row.latency_ms_client for row in rows]
        summary[backend] = {
            "n": len(rows),
            "errors": sum(1 for row in rows if row.error),
            "cache_hits": sum(1 for row in rows if row.cache_hit),
            "latency_client_avg_ms": round(statistics.fmean(latencies), 3),
            "latency_client_p50_ms": round(statistics.median(latencies), 3),
            "latency_client_p95_ms": round(percentile(latencies, 0.95), 3),
            "citation_accuracy_avg": round(
                statistics.fmean(row.citation_accuracy for row in rows),
                4,
            ),
            "answer_exactness_avg": round(
                statistics.fmean(row.answer_exactness for row in rows),
                4,
            ),
            "answer_chars_avg": round(
                statistics.fmean(row.answer_chars for row in rows),
                1,
            ),
        }
    return summary


def percentile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = min(len(ordered) - 1, max(0, round((len(ordered) - 1) * q)))
    return ordered[idx]


def write_report(output_path: Path, payload: dict[str, Any]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path = output_path.with_suffix(".md")
    summary = payload["summary"]
    rows = payload["results"]
    lines = [
        "# RAG API Embedding Benchmark",
        "",
        "## Summary",
        "",
        (
            "| backend | n | errors | cache hits | avg ms | p50 ms | p95 ms | "
            "citation avg | exactness avg | chars avg |"
        ),
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for backend, data in summary.items():
        lines.append(
            "| {backend} | {n} | {errors} | {cache_hits} | {avg} | {p50} | {p95} | "
            "{citation} | {exactness} | {chars} |".format(
                backend=backend,
                n=data["n"],
                errors=data["errors"],
                cache_hits=data["cache_hits"],
                avg=data["latency_client_avg_ms"],
                p50=data["latency_client_p50_ms"],
                p95=data["latency_client_p95_ms"],
                citation=data["citation_accuracy_avg"],
                exactness=data["answer_exactness_avg"],
                chars=data["answer_chars_avg"],
            )
        )
    lines.extend(
        [
            "",
            "## Cases",
            "",
            "| backend | case | status | ms | citation | exactness | cache | error |",
            "|---|---|---:|---:|---:|---:|---|---|",
        ]
    )
    for row in rows:
        row_error = (row.get("error") or "").replace("|", "\\|")
        row_fmt = {**row, "error": row_error}
        lines.append(
            "| {backend} | {case_id} | {status_code} | {latency_ms_client} | "
            "{citation_accuracy} | {answer_exactness} | {cache_hit} | {error} |".format(
                **row_fmt,
            )
        )
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--golden", type=Path, default=Path("tests/evals/rag_sp_ce_golden.jsonl"))
    parser.add_argument("--normal-model", default="data/rag/models/temp_pytorch")
    parser.add_argument("--onnx-model", default="data/rag/models/enel-minilm-onnx")
    parser.add_argument(
        "--normal-chroma",
        type=Path,
        default=Path("data/rag/bench/chromadb-normal"),
    )
    parser.add_argument(
        "--onnx-chroma",
        type=Path,
        default=Path("data/rag/bench/chromadb-onnx"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/rag/eval_reports/api_embedding_benchmark.json"),
    )
    parser.add_argument("--no-rebuild", action="store_true")
    parser.add_argument("--no-rebuild-normal", action="store_true")
    parser.add_argument("--no-rebuild-onnx", action="store_true")
    parser.add_argument("--allow-known-cache", action="store_true")
    parser.add_argument("--provider", default="stub")
    parser.add_argument(
        "--model-path",
        type=Path,
        default=Path("data/rag/models/qwen2.5-3b-instruct-q4_k_m.gguf"),
    )
    parser.add_argument("--n-ctx", type=int, default=2048)
    parser.add_argument("--n-threads", type=int, default=4)
    parser.add_argument("--max-turn-tokens", type=int, default=512)
    args = parser.parse_args()

    base_config = load_rag_config()
    cases = load_cases(args.golden, DEFAULT_CASE_IDS)
    normal_model = Path(args.normal_model)
    normal_embedding_model = (
        str(normal_model)
        if normal_model.exists()
        else "sentence-transformers/all-MiniLM-L6-v2"
    )
    configs = {
        "normal": replace(
            base_config,
            provider=args.provider,
            model_path=args.model_path,
            embedding_model=normal_embedding_model,
            chromadb_path=args.normal_chroma,
            max_turn_tokens=args.max_turn_tokens,
            max_context_tokens=args.n_ctx,
            n_ctx=args.n_ctx,
            n_threads=args.n_threads,
            temperature=0.0,
            telemetry_path=Path("/tmp/rag_api_bench_normal_telemetry.jsonl"),
            feedback_path=Path("/tmp/rag_api_bench_normal_feedback.csv"),
            llm_judge_enabled=False,
        ),
        "onnx": replace(
            base_config,
            provider=args.provider,
            model_path=args.model_path,
            embedding_model=args.onnx_model,
            chromadb_path=args.onnx_chroma,
            max_turn_tokens=args.max_turn_tokens,
            max_context_tokens=args.n_ctx,
            n_ctx=args.n_ctx,
            n_threads=args.n_threads,
            temperature=0.0,
            telemetry_path=Path("/tmp/rag_api_bench_onnx_telemetry.jsonl"),
            feedback_path=Path("/tmp/rag_api_bench_onnx_feedback.csv"),
            llm_judge_enabled=False,
        ),
    }

    all_results: list[BenchResult] = []
    for backend, config in configs.items():
        print(f"[bench] backend={backend} embedding={config.embedding_model}", flush=True)
        all_results.extend(
            benchmark_backend(
                backend=backend,
                config=config,
                cases=cases,
                rebuild=(
                    not args.no_rebuild
                    and not (backend == "normal" and args.no_rebuild_normal)
                    and not (backend == "onnx" and args.no_rebuild_onnx)
                ),
                disable_known_cache=not args.allow_known_cache,
            )
        )

    payload = {
        "normal_config": json_safe(asdict(configs["normal"])),
        "onnx_config": json_safe(asdict(configs["onnx"])),
        "case_ids": list(DEFAULT_CASE_IDS),
        "summary": summarize(all_results),
        "results": [asdict(result) for result in all_results],
    }
    write_report(args.output, payload)
    print(json.dumps(payload["summary"], ensure_ascii=False, indent=2))
    print(f"[bench] report_json={args.output}")
    print(f"[bench] report_md={args.output.with_suffix('.md')}")
    return 0


def json_safe(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, tuple):
        return [json_safe(item) for item in value]
    if isinstance(value, list):
        return [json_safe(item) for item in value]
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    return value


if __name__ == "__main__":
    raise SystemExit(main())
