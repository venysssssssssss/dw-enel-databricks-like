import argparse
import json
import logging
import asyncio
import random
from pathlib import Path
import pandas as pd

from src.data_plane.store import DataStore
from src.rag.teachers.gemini_client import GeminiTeacherClient
from src.rag.redact_pii import redact_pii

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

FAMILIES = {
    1: {"name": "Volumetria agregada", "budget": 80},
    2: {"name": "Top-N analítico", "budget": 60},
    3: {"name": "Comparativos região × tempo", "budget": 50},
    4: {"name": "Drill-down causal", "budget": 70},
    5: {"name": "Regras de negócio", "budget": 45},
    6: {"name": "Modelagem ML", "budget": 40},
    7: {"name": "Operacional / runbook", "budget": 35},
    8: {"name": "Adversariais / fora-de-escopo", "budget": 50},
}

def get_context():
    """Coleta o contexto real da ENEL para enviar ao professor."""
    store = DataStore()
    
    # 1. Esquema silver (colunas e tipos)
    silver = store.load_silver(include_total=True)
    schema = {col: str(dtype) for col, dtype in silver.dtypes.items()}
    
    # 2. Top-N causas canônicas
    top_causas = silver["causa_canonica"].value_counts().head(20).to_dict()
    
    # 3. Lista de documentos
    docs = []
    for root in ["docs/business-rules/", "docs/ml/", "docs/api/", "docs/RUNBOOK.md"]:
        p = Path(root)
        if p.is_file():
            docs.append(str(p))
        elif p.is_dir():
            docs.extend([str(f) for f in p.glob("*.md")])
            
    # 4. Amostra anonimizada de descrições
    sample_desc = []
    if "observacao_ordem" in silver.columns:
        # Pega 50 descrições não nulas aleatórias
        valid_desc = silver[silver["observacao_ordem"].notna()]["observacao_ordem"].tolist()
        if valid_desc:
            sample_desc = random.sample(valid_desc, min(50, len(valid_desc)))
            sample_desc = [redact_pii(d) for d in sample_desc]

    context = {
        "schema_silver": schema,
        "top_causas_canonicas": top_causas,
        "docs_disponiveis": docs,
        "amostra_descricoes": sample_desc,
        "glossario": ["ACF/ASF", "UT", "CO", "UC", "Lote", "Procedente", "Improcedente"]
    }
    return context

async def generate_questions(round_num: int, seed: int):
    random.seed(seed)
    logger.info(f"Iniciando geração para round {round_num} com seed {seed}")
    
    context = get_context()
    
    output_dir = Path(f"data/rag_train/round-{round_num:03d}")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "questions.jsonl"
    
    teacher = GeminiTeacherClient()
    
    logger.info(f"Chamando Gemini ({teacher.model}) para gerar perguntas...")
    
    families_budget = {fid: info["budget"] for fid, info in FAMILIES.items()}
    
    try:
        questions = await teacher.generate_questions(json.dumps(context, ensure_ascii=False), families_budget)
        
        with open(output_file, "w", encoding="utf-8") as f:
            for q in questions:
                # Garante que id seja único se Gemini falhar em seguir o budget ou IDs
                f.write(json.dumps(q, ensure_ascii=False) + "\n")
                
        logger.info(f"Sucesso: geradas {len(questions)} perguntas em {output_file}")
    except Exception as e:
        logger.error(f"Erro na geração: {e}")
        # Fallback para mock se falhar (opcional, mas aqui vamos deixar falhar para o usuário ver)
        raise e

async def main():
    parser = argparse.ArgumentParser(description="Generate RAG questions via Gemini-3 Flash")
    parser.add_argument("--rounds", type=int, default=1, help="Número de rounds para gerar")
    parser.add_argument("--seed", type=int, default=26, help="Seed aleatória para geração determinística")
    args = parser.parse_args()
    
    for r in range(1, args.rounds + 1):
        await generate_questions(r, args.seed)

if __name__ == "__main__":
    asyncio.run(main())
