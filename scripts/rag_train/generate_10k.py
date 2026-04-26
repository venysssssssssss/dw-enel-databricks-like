import pandas as pd
import json
import random
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

def generate_10k():
    logger.info("Gerando 10.000 perguntas para treino do Qwen 2.5...")
    
    silver_path = Path("data/silver/erro_leitura_normalizado.csv")
    df = pd.read_csv(silver_path, low_memory=False)
    
    # Entidades por região
    regions = ["CE", "SP"]
    entities = {reg: {
        "assuntos": df[df["_source_region"] == reg]["assunto"].unique().tolist(),
        "causas": df[df["_source_region"] == reg]["causa_raiz"].dropna().unique().tolist(),
        "instalacoes": df[df["_source_region"] == reg]["instalacao"].unique().tolist()
    } for reg in regions}

    questions = []
    
    templates = [
        ("Qual a principal causa de reclamação de {entidade} em {reg}?", 1),
        ("Volume de ordens para {entidade} na regional {reg}.", 1),
        ("Top 5 instalações com problemas de {entidade} em {reg}.", 2),
        ("Como {entidade} afeta o refaturamento em {reg}?", 4),
        ("Explique a regra de {reg} para {entidade}.", 5),
        ("Existe PII na instalação {entidade}?", 8),
        ("Qual o padrão de sazonalidade para {entidade} em {reg}?", 3)
    ]

    while len(questions) < 10000:
        reg = random.choice(regions)
        template, family = random.choice(templates)
        
        reg_entities = entities[reg]
        if family == 8:
            entidade = str(random.choice(reg_entities["instalacoes"])) if reg_entities["instalacoes"] else "0000"
        else:
            candidates = reg_entities["assuntos"] + reg_entities["causas"]
            entidade = random.choice(candidates) if candidates else "Geral"
            
        questions.append({
            "id": f"Q-10K-{len(questions):05d}",
            "family": family,
            "region": reg,
            "question": template.format(entidade=entidade, reg=reg),
            "gold_answer": f"Resposta esperada para {entidade} em {reg}.",
            "expected_sources": [] 
        })

    output_dir = Path("data/rag_train/round-10k")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "questions.jsonl"
    
    with open(output_file, "w", encoding="utf-8") as f:
        for q in questions:
            f.write(json.dumps(q, ensure_ascii=False) + "\n")
            
    logger.info(f"Sucesso: 10.000 perguntas geradas em {output_file}")

if __name__ == "__main__":
    generate_10k()
