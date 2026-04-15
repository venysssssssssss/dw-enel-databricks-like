"""Avaliação gabarito: roda 10 perguntas-chave e checa citation_rate + latência.

Não usa LLM (modo stub), focando em validar retrieval + pipeline. Com LLM real
(llama-cpp), extrapole adicionando métricas de fidelidade manual.
"""

from __future__ import annotations

import json
import sys
import time
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.rag.config import load_rag_config  # noqa: E402
from src.rag.orchestrator import RagOrchestrator  # noqa: E402


@dataclass(frozen=True, slots=True)
class EvalCase:
    question: str
    expected_source_fragment: str  # substring que deve aparecer em alguma fonte
    min_passages: int = 1


CASES: list[EvalCase] = [
    EvalCase("O que é ACF/ASF?", "business-rules"),
    EvalCase("Quais os KPIs da Sprint 13?", "sprint-13"),
    EvalCase("Como funciona a ingestão Bronze?", "architecture"),
    EvalCase("Quais macro-temas existem para reclamações CE?", "viz", min_passages=1),
    EvalCase("Quais modelos de ML são usados?", "ml"),
    EvalCase("Quais endpoints FastAPI existem?", "api"),
    EvalCase("Como rodar o pipeline localmente?", "RUNBOOK"),
    EvalCase("Quais camadas o lakehouse possui?", "architecture"),
    EvalCase("Quais variáveis de ambiente existem?", "ENV"),
    EvalCase("Como o dashboard classifica erros de leitura?", "sprint"),
]


def run() -> int:
    config = load_rag_config()
    orch = RagOrchestrator(config)

    passed = 0
    citation_ok = 0
    total_ms = 0.0
    rows = []
    for case in CASES:
        t0 = time.perf_counter()
        resp = orch.answer(case.question)
        dt_ms = (time.perf_counter() - t0) * 1000
        total_ms += dt_ms
        found = any(case.expected_source_fragment.lower() in p.source_path.lower() for p in resp.passages)
        has_passages = len(resp.passages) >= case.min_passages
        ok = found and has_passages
        passed += int(ok)
        citation_ok += int(len(resp.passages) > 0)
        rows.append(
            {
                "question": case.question,
                "expected_in": case.expected_source_fragment,
                "passages": [p.source_path for p in resp.passages],
                "intent": resp.intent,
                "latency_ms": round(dt_ms, 1),
                "pass": ok,
            }
        )

    summary = {
        "cases": len(CASES),
        "passed": passed,
        "accuracy": round(passed / len(CASES), 3),
        "citation_rate": round(citation_ok / len(CASES), 3),
        "avg_latency_ms": round(total_ms / len(CASES), 1),
        "rows": rows,
    }
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    # CI check (lenient porque modo stub não responde com fluência, só retrieval)
    return 0 if summary["accuracy"] >= 0.6 and summary["citation_rate"] >= 0.8 else 1


if __name__ == "__main__":
    sys.exit(run())
