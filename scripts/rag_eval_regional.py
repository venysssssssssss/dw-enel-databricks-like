"""CLI de avaliação regional CE/SP com gates de qualidade."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.rag.config import load_rag_config  # noqa: E402
from src.rag.eval.runner import run_eval  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Avaliação RAG regional CE/SP")
    parser.add_argument("--golden", required=True, type=Path)
    parser.add_argument("--gate-recall5", type=float, default=0.85)
    parser.add_argument("--gate-regional-compliance", type=float, default=1.0)
    parser.add_argument("--gate-refusal", type=float, default=0.95)
    parser.add_argument("--gate-citation", type=float, default=0.80)
    parser.add_argument("--gate-exactness", type=float, default=0.75)
    parser.add_argument("--gate-fallback-guardrail", type=float, default=0.95)
    parser.add_argument("--dataset-version", type=str, default=None)
    args = parser.parse_args()

    config = load_rag_config()
    report = run_eval(config, golden_path=args.golden, dataset_version=args.dataset_version)
    metrics = report["metrics"]

    gates = {
        "recall@5": metrics["recall@5"] >= args.gate_recall5,
        "regional_compliance": metrics["regional_compliance"] >= args.gate_regional_compliance,
        "refusal_rate": metrics["refusal_rate"] >= args.gate_refusal,
        "fallback_guardrail_success": (
            metrics["fallback_guardrail_success"] >= args.gate_fallback_guardrail
        ),
        "citation_accuracy": metrics["citation_accuracy"] >= args.gate_citation,
        "answer_exactness": metrics["answer_exactness"] >= args.gate_exactness,
    }
    report["gates"] = gates
    report["all_gates_pass"] = all(gates.values())

    out_dir = Path("data/rag/eval_reports")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}.json"
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(
        " | ".join(
            [
                f"recall@5={metrics['recall@5']:.2f}",
                f"MRR={metrics['mrr@10']:.2f}",
                f"citation={metrics['citation_accuracy']:.2f}",
                f"regional={metrics['regional_compliance']:.2f}",
                f"refusal={metrics['refusal_rate']:.2f}",
                f"fallback_guardrail={metrics['fallback_guardrail_success']:.2f}",
                f"exactness={metrics['answer_exactness']:.2f}",
                f"p50={metrics['latency_p50_ms']:.1f}ms",
                f"p95={metrics['latency_p95_ms']:.1f}ms",
            ]
        )
    )
    print(f"report={out_path}")
    print("✓ ALL GATES PASS" if report["all_gates_pass"] else "✗ GATE FAILURE")
    return 0 if report["all_gates_pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
