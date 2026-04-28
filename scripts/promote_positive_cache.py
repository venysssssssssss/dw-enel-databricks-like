"""Promote frequently-asked, low-feedback-risk answers to the PositiveCache.

Reads `data/rag/telemetry.jsonl` + `data/rag/feedback.csv` and, for each
question that hit ≥ MIN_REPEATS misses without any "down" feedback, runs the
RagOrchestrator once to capture the answer and stores it in
`data/rag_train/positive_cache.parquet` keyed by canonical/token-set hashes.

Effect: future identical (or template-equivalent) questions short-circuit
the LLM call, cutting p95 latency dramatically for recurring traffic.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.rag.cache.positive_cache import PositiveCache  # noqa: E402

DEFAULT_TELEMETRY = ROOT / "data/rag/telemetry.jsonl"
DEFAULT_FEEDBACK = ROOT / "data/rag/feedback.csv"
DEFAULT_OUTPUT = ROOT / "data/rag_train/positive_cache.parquet"


def _load_telemetry(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def _load_feedback(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    out: dict[str, str] = {}
    with path.open(encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            qh = (row.get("question_hash") or "").strip()
            rating = (row.get("rating") or "").strip().lower()
            if qh and rating in {"up", "down"}:
                # último voto vence
                out[qh] = rating
    return out


def _candidates(
    rows: list[dict[str, Any]],
    feedback: dict[str, str],
    *,
    min_repeats: int,
) -> list[tuple[str, int, dict[str, Any]]]:
    """Retorna (question_preview, count, sample_row) para promoção."""
    by_preview: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in rows:
        if r.get("provider") == "stub":
            continue
        preview = (r.get("question_preview") or "").strip()
        if len(preview) < 20:
            continue
        by_preview[preview].append(r)

    out: list[tuple[str, int, dict[str, Any]]] = []
    for preview, group in by_preview.items():
        if len(group) < min_repeats:
            continue
        # Veta se houve feedback negativo associado.
        if any(feedback.get(r.get("question_hash") or "") == "down" for r in group):
            continue
        # Pega turno mais recente como amostra.
        sample = max(group, key=lambda r: r.get("ts", ""))
        out.append((preview, len(group), sample))
    out.sort(key=lambda t: t[1], reverse=True)
    return out


def _generate_answers(
    candidates: list[tuple[str, int, dict[str, Any]]],
    *,
    limit: int,
    dry_run: bool,
) -> list[dict[str, Any]]:
    if dry_run or not candidates:
        return [
            {
                "preview": p,
                "count": c,
                "intent": s.get("intent_class"),
                "region": s.get("region_detected"),
            }
            for p, c, s in candidates[:limit]
        ]

    # Importação tardia: orchestrator carrega chromadb + llama-cpp.
    from src.rag.config import load_rag_config
    from src.rag.orchestrator import RagOrchestrator

    config = load_rag_config()
    orchestrator = RagOrchestrator(config)
    out: list[dict[str, Any]] = []
    for preview, count, sample in candidates[:limit]:
        # Preview vem truncado em 80 chars; preferimos a forma completa quando
        # disponível em telemetry.extra (não logada por padrão). Aqui usamos
        # preview mesmo — melhor cache parcial que nada.
        question = preview
        try:
            response = orchestrator.answer(question)
        except Exception as exc:
            print(f"[skip] {question[:60]}…: {exc}")
            continue
        if not response.text or len(response.text) < 40:
            continue
        canonical = PositiveCache.canonicalize(question)
        token_set = PositiveCache.tokenize(question)
        out.append(
            {
                "question_preview": question,
                "answer": response.text,
                "intent": response.intent,
                "region": response.region_detected,
                "count": count,
                "token_hash": PositiveCache._sha(token_set),  # noqa: SLF001
                "hash": PositiveCache._sha(canonical),
            }
        )
    return out


def _persist(entries: list[dict[str, Any]], output: Path) -> int:
    if not entries:
        return 0
    import pandas as pd

    output.parent.mkdir(parents=True, exist_ok=True)
    new_df = pd.DataFrame(entries)
    if output.exists():
        try:
            existing = pd.read_parquet(output)
            combined = pd.concat([existing, new_df], ignore_index=True)
            combined = combined.drop_duplicates(subset=["token_hash"], keep="last")
        except Exception:
            combined = new_df
    else:
        combined = new_df
    combined.to_parquet(output, index=False)
    return len(combined)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--telemetry", type=Path, default=DEFAULT_TELEMETRY)
    parser.add_argument("--feedback", type=Path, default=DEFAULT_FEEDBACK)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--min-repeats", type=int, default=3)
    parser.add_argument("--limit", type=int, default=30, help="Máximo de respostas a gerar nesta rodada.")
    parser.add_argument("--dry-run", action="store_true", help="Apenas lista candidatos.")
    args = parser.parse_args()

    rows = _load_telemetry(args.telemetry)
    feedback = _load_feedback(args.feedback)
    candidates = _candidates(rows, feedback, min_repeats=args.min_repeats)
    print(f"[promote] candidates={len(candidates)} (min_repeats={args.min_repeats})")
    for preview, count, _ in candidates[: args.limit]:
        print(f"  · {count:>3}× {preview[:90]}")

    entries = _generate_answers(candidates, limit=args.limit, dry_run=args.dry_run)
    if args.dry_run:
        print(f"[dry-run] {len(entries)} candidates would be promoted.")
        return 0
    total = _persist(entries, args.output)
    print(f"[promote] generated={len(entries)} cache_total={total} → {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
