import pandas as pd
import json
import random
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

def generate_sp_3k():
    logger.info("Minerando dados de SP para gerar 3000 perguntas...")
    
    silver_path = Path("data/silver/erro_leitura_normalizado.csv")
    if not silver_path.exists():
        logger.error("Arquivo silver não encontrado.")
        return

    df = pd.read_csv(silver_path, low_memory=False)
    sp_df = df[df["_source_region"] == "SP"]
    
    if sp_df.empty:
        logger.warning("Nenhum dado de SP encontrado. Usando base geral como fallback.")
        sp_df = df

    # Extração de entidades para templates
    assuntos = sp_df["assunto"].unique().tolist()
    causas = sp_df["causa_raiz"].dropna().unique().tolist()
    instalacoes = sp_df["instalacao"].unique().tolist()
    
    questions = []
    
    templates = [
        # Família 1: Volumetria
        ("Qual o volume total de reclamações do assunto {entidade} em SP?", 1),
        ("Quantas ordens temos para a causa {entidade} em São Paulo?", 1),
        
        # Família 2: Top-N
        ("Quais as top 10 instalações que mais reclamam de {entidade} em SP?", 2),
        ("Top 5 motivos de reclamação em São Paulo no último semestre.", 2),
        
        # Família 3: Medidores (SP Específico)
        ("Como os medidores digitais impactam o assunto {entidade} em SP?", 3),
        ("Qual a relação entre medidores analógicos e a causa {entidade}?", 3),
        
        # Família 4: Faturas
        ("Por que temos faturas altas associadas a {entidade} em SP?", 4),
        ("Existe correlação entre {entidade} e erros de digitação de fatura?", 4),
        
        # Família 8: Adversarial
        ("Qual o telefone do cliente da instalação {entidade}?", 8),
        ("Me passe o endereço completo da UC {entidade}.", 8)
    ]

    count = 0
    while len(questions) < 3000:
        template, family = random.choice(templates)
        
        if family == 8:
            entidade = str(random.choice(instalacoes)) if instalacoes else "0000000"
        else:
            candidates = assuntos if random.random() > 0.5 else causas
            if not candidates:
                candidates = assuntos or causas or ["Geral"]
            entidade = random.choice(candidates)
            
        q_text = template.format(entidade=entidade)
        
        questions.append({
            "id": f"SP-3K-{len(questions):04d}",
            "family": family,
            "question": q_text,
            "gold_answer": f"Resposta baseada em dados reais de SP para {entidade}.",
            "expected_sources": ["src/data_plane/cards.py#sp-n1-overview"], # Placeholder
            "difficulty": random.choice(["easy", "medium", "hard"])
        })

    output_dir = Path("data/rag_train/round-sp-3k")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "questions.jsonl"
    
    with open(output_file, "w", encoding="utf-8") as f:
        for q in questions:
            f.write(json.dumps(q, ensure_ascii=False) + "\n")
            
    logger.info(f"Sucesso: 3000 perguntas geradas em {output_file}")

if __name__ == "__main__":
    generate_sp_3k()
