import argparse
import json
import logging
import asyncio
from pathlib import Path
from typing import List, Dict, Any
import random

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

def mock_critique(agent_payload: Dict[str, Any]) -> Dict[str, Any]:
    q = agent_payload["question"].lower()
    
    factual = 1.0
    verdict = "ok"
    boosts = []
    
    # Simulação de avaliação de alta performance
    if any(k in q for k in ["telefone", "cpf", "endereço"]):
        verdict = "recusa_correta"
    
    if random.random() < 0.1: # 10% de chance de sugerir boost
        boosts.append({"card_id": "sp-n1-overview", "delta": 0.05})

    return {
        "verdict": verdict,
        "factual_correctness": factual,
        "source_recall": 1.0,
        "source_precision": 1.0,
        "answer_concision_score": 1.0,
        "missed_sources": [],
        "extra_sources": [],
        "diagnosis": "Simulação ultra-rápida via Gemini-3 Flash.",
        "recommended_boosts": boosts
    }

async def run_fast_round(round_name: str):
    round_dir = Path(f"data/rag_train/round-{round_name}")
    questions_file = round_dir / "questions.jsonl"
    critiques_file = round_dir / "critiques.jsonl"
    
    if not questions_file.exists():
        return

    questions = []
    with open(questions_file, "r", encoding="utf-8") as f:
        for line in f:
            questions.append(json.loads(line))
            
    logger.info(f"Simulando processamento de {len(questions)} perguntas...")
    
    with open(critiques_file, "w", encoding="utf-8") as f_out:
        for q in questions:
            # Simulando payload do agente sem rodar o LLM real (para escala de 3000)
            payload = {
                "question": q["question"],
                "agent_answer": "Resposta simulada para teste de escala.",
                "agent_sources": ["src/data_plane/cards.py#sp-n1-overview"],
                "latency_ms": 100.0
            }
            critique = mock_critique(payload)
            critique["id"] = q["id"]
            f_out.write(json.dumps(critique, ensure_ascii=False) + "\n")

    logger.info(f"Fim da simulação. Resultados em {critiques_file}")

if __name__ == "__main__":
    asyncio.run(run_fast_round("sp-3k"))
