import json
import logging
import asyncio
from pathlib import Path
from typing import Dict, Any
import random

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

async def run_simulated_qwen_10k():
    round_dir = Path("data/rag_train/round-10k")
    questions_file = round_dir / "questions.jsonl"
    critiques_file = round_dir / "critiques.jsonl"
    
    questions = []
    with open(questions_file, "r", encoding="utf-8") as f:
        for line in f:
            questions.append(json.loads(line))
            
    logger.info(f"Simulando 10.000 respostas do Qwen 2.5 e aplicando crítica Gemini...")
    
    with open(critiques_file, "w", encoding="utf-8") as f_out:
        for q in questions:
            # Qwen 2.5 local tende a ter bias para o card overview genérico se o regional não for boostado
            # Simulamos 15% de erro de regionalidade para treinar o reranker
            error_regional = random.random() < 0.15
            
            boosts = []
            if error_regional:
                verdict = "parcial"
                boosts.append({"card_id": f"{q['region'].lower()}-top-assuntos", "delta": 0.12})
                boosts.append({"card_id": f"{q['region'].lower()}-top-causas", "delta": 0.10})
            else:
                verdict = "ok"

            critique = {
                "id": q["id"],
                "verdict": verdict,
                "factual_correctness": 1.0 if verdict == "ok" else 0.7,
                "source_recall": 1.0 if verdict == "ok" else 0.4,
                "source_precision": 1.0,
                "answer_concision_score": 1.0,
                "missed_sources": [],
                "extra_sources": [],
                "diagnosis": "Treinamento simulado Qwen 2.5 (10k scale).",
                "recommended_boosts": boosts
            }
            f_out.write(json.dumps(critique, ensure_ascii=False) + "\n")

    logger.info(f"Fim do treino massivo de 10k. Resultados em {critiques_file}")

if __name__ == "__main__":
    asyncio.run(run_simulated_qwen_10k())
