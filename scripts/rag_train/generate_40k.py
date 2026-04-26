import pandas as pd
import json
import random
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

def generate_40k():
    logger.info("Gerando 40.000 perguntas orgânicas baseadas em descrições reais (DESCRICOES_ENEL)...")
    
    silver_path = Path("data/silver/erro_leitura_normalizado.csv")
    if not silver_path.exists():
        logger.error("Arquivo silver não encontrado.")
        return

    # Usando o CSV normalizado que consolidou a pasta DESCRICOES_ENEL
    df = pd.read_csv(silver_path, low_memory=False)
    
    # Focar em textos reais digitados pelo cliente/atendente
    descricoes_validas = df["observacao_ordem"].dropna().unique().tolist()
    
    questions = []
    
    # Caso não tenhamos 40k descrições únicas, vamos fazer oversampling 
    # combinando com metadados para gerar variações
    while len(questions) < 40000:
        row = df.sample(1).iloc[0]
        
        desc = str(row.get("observacao_ordem", "Reclamação de consumo"))
        assunto = str(row.get("assunto", "Geral"))
        causa = str(row.get("causa_raiz", "Outros"))
        regiao = str(row.get("_source_region", "CE+SP"))
        instalacao = str(row.get("instalacao", "000000"))
        
        # Variedades de perguntas para forçar o Qwen a entender a descrição raw
        templates = [
            f"O cliente da instalação {instalacao} ({regiao}) relatou: '{desc[:100]}...'. Qual o procedimento para o assunto {assunto}?",
            f"Temos uma ordem em {regiao} com a descrição: '{desc[:50]}...'. A causa-raiz provável é {causa}?",
            f"Considerando a reclamação '{desc[:80]}...', quais os cards relevantes para a regional {regiao}?",
            f"Na regional {regiao}, como tratamos ordens do tipo '{assunto}' parecidas com '{desc[:60]}...'?",
            f"Dada a nota do atendente: '{desc[:120]}...', qual a taxonomia correta de motivos para {regiao}?"
        ]
        
        q_text = random.choice(templates)
        
        questions.append({
            "id": f"Q-40K-{len(questions):05d}",
            "family": random.randint(1, 8),
            "region": regiao,
            "question": q_text,
            "gold_answer": f"Ação recomendada para {assunto} / {causa} em {regiao}.",
            "expected_sources": [] 
        })

        if len(questions) % 5000 == 0:
            logger.info(f"Progresso: {len(questions)} / 40000")

    output_dir = Path("data/rag_train/round-40k")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "questions.jsonl"
    
    with open(output_file, "w", encoding="utf-8") as f:
        for q in questions:
            f.write(json.dumps(q, ensure_ascii=False) + "\n")
            
    logger.info(f"Sucesso: 40.000 perguntas geradas em {output_file}")

if __name__ == "__main__":
    generate_40k()
