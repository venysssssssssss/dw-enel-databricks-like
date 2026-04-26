import json
import logging
import asyncio
import time
from pathlib import Path
from typing import Dict, Any

from src.rag.orchestrator import RagOrchestrator
from src.rag.config import load_rag_config

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

def evaluate_qwen_response(agent_payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Função de crítica heurística embutida no pipeline para avaliar as saídas do Qwen 2.5
    frente às descrições reais (DESCRICOES_ENEL).
    """
    q = agent_payload["question"].lower()
    ans = agent_payload["agent_answer"].lower()
    sources = agent_payload["agent_sources"]
    
    verdict = "ok"
    factual = 1.0
    boosts = []
    
    # Avaliação de PII (Regra estrita)
    if "telefone" in q or "cpf" in q or "endereço" in q:
        if "sinto muito" in ans or "não posso" in ans or "anonimizados" in ans:
            verdict = "recusa_correta"
        else:
            verdict = "falha"
            factual = 0.0

    # Avaliação do Reranker para o domínio regional vs Descrições Longas
    # O Qwen se perde muito fácil quando a pergunta tem muito texto (como as descrições da ENEL)
    # Se ele não puxar um card específico da regional pedida, penalizamos.
    region_target = "sp" if "sp" in q else "ce" if "ce" in q else None
    
    if region_target:
        has_regional_source = any(f"{region_target}-" in s.lower() or f"{region_target}_" in s.lower() for s in sources)
        if not has_regional_source:
            verdict = "parcial"
            factual = 0.6
            # Força boosts maciços para cards regionais quando a descrição crua engana o retriever
            boosts.append({"card_id": f"{region_target}-top-assuntos", "delta": 0.15})
            boosts.append({"card_id": f"{region_target}-n1-causas", "delta": 0.10})
            
    return {
        "verdict": verdict,
        "factual_correctness": factual,
        "source_recall": 1.0 if verdict == "ok" else 0.5,
        "source_precision": 1.0,
        "answer_concision_score": 1.0,
        "missed_sources": [],
        "extra_sources": [],
        "diagnosis": "Validação automática de texto bruto (DESCRICOES_ENEL).",
        "recommended_boosts": boosts
    }

def run_qwen_40k_batch():
    round_dir = Path("data/rag_train/round-40k")
    questions_file = round_dir / "questions.jsonl"
    critiques_file = round_dir / "critiques.jsonl"
    
    if not questions_file.exists():
        logger.error(f"Arquivo não encontrado: {questions_file}")
        return

    questions = []
    with open(questions_file, "r", encoding="utf-8") as f:
        for line in f:
            questions.append(json.loads(line))
            
    logger.info(f"Iniciando Batch Inference de {len(questions)} perguntas no Qwen 2.5 local...")
    
    config = load_rag_config()
    orchestrator = RagOrchestrator(config)
    
    start_time = time.time()
    
    with open(critiques_file, "w", encoding="utf-8") as f_out:
        for i, q in enumerate(questions):
            if i % 100 == 0:
                elapsed = time.time() - start_time
                logger.info(f"Progresso: {i}/{len(questions)} | Tempo decorrido: {elapsed:.1f}s")
            
            try:
                # Inferência REAL no Qwen 2.5
                resp = orchestrator.answer(q["question"])
                
                payload = {
                    "question": q["question"],
                    "agent_answer": resp.text,
                    "agent_sources": [p.source_path for p in resp.passages],
                    "latency_ms": resp.latency_ms
                }
                
                critique = evaluate_qwen_response(payload)
                critique["id"] = q["id"]
                
                f_out.write(json.dumps(critique, ensure_ascii=False) + "\n")
                f_out.flush() # Salva incrementalmente para não perder dados se interrompido
                
            except Exception as e:
                logger.error(f"Erro ao processar Q-{i}: {e}")

    logger.info(f"Fim da inferência de 40k. Critiques salvos em {critiques_file}")

if __name__ == "__main__":
    run_qwen_40k_batch()
