import argparse
import json
import logging
import asyncio
from pathlib import Path
from typing import List, Dict, Any

from src.rag.orchestrator import RagOrchestrator
from src.rag.config import load_rag_config
from src.rag.teachers.gemini_client import GeminiTeacherClient

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

async def run_round(round_num: int, teacher_model: str):
    logger.info(f"Iniciando execução da round {round_num}")
    
    round_dir = Path(f"data/rag_train/round-{round_num:03d}")
    questions_file = round_dir / "questions.jsonl"
    critiques_file = round_dir / "critiques.jsonl"
    
    if not questions_file.exists():
        logger.error(f"Arquivo de perguntas não encontrado: {questions_file}")
        return

    config = load_rag_config()
    orchestrator = RagOrchestrator(config)
    teacher = GeminiTeacherClient(model=teacher_model)
    
    questions = []
    with open(questions_file, "r", encoding="utf-8") as f:
        for line in f:
            questions.append(json.loads(line))
            
    logger.info(f"Processando {len(questions)} perguntas...")
    
    critiques = []
    for q in questions:
        logger.info(f"Executando RAG local para: {q['id']}")
        
        # 1. Chama RAG local
        try:
            resp = orchestrator.answer(q["question"])
            
            agent_payload = {
                "question": q["question"],
                "gold_answer": q["gold_answer"],
                "expected_sources": q["expected_sources"],
                "agent_answer": resp.text,
                "agent_sources": [p.source_path for p in resp.passages],
                "latency_ms": resp.latency_ms,
                "intent": resp.intent
            }
            
            # 2. Critica via Gemini
            logger.info(f"Solicitando crítica ao professor para: {q['id']}")
            critique = await teacher.critique(agent_payload)
            critique["id"] = q["id"] # Garante ID correto
            
            critiques.append(critique)
            
            # Salva incrementalmente
            with open(critiques_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(critique, ensure_ascii=False) + "\n")
                
        except Exception as e:
            logger.error(f"Erro ao processar {q['id']}: {e}")
            continue
            
    logger.info(f"Rodada concluída. Critiques salvos em {critiques_file}")

def main():
    parser = argparse.ArgumentParser(description="Run RAG round and generate critiques")
    parser.add_argument("--round", type=int, required=True, help="Número da round")
    parser.add_argument("--teacher", type=str, default="gemini-1.5-flash", help="Modelo Gemini professor")
    args = parser.parse_args()
    
    asyncio.run(run_round(args.round, args.teacher))

if __name__ == "__main__":
    main()
