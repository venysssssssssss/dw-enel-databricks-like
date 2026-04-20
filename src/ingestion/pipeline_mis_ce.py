"""Pipeline de Ingestão e Tratamento (Bronze/Silver) - Reclamações CE (MIS Aconchegante)."""

import os
import re
import glob
from pathlib import Path

import pandas as pd
from loguru import logger

# Regex para remoção de PII
_CPF_RE = re.compile(r"\b\d{3}[\.\s]?\d{3}[\.\s]?\d{3}[-\.\s]?\d{2}\b")
_TELEFONE_RE = re.compile(r"\b(?:\+?55\s?)?(?:\(?\d{2}\)?\s?)?9?\d{4}[-\.\s]?\d{4}\b")
_CNPJ_RE = re.compile(r"\b\d{2}[\.\s]?\d{3}[\.\s]?\d{3}[\/\s]?\d{4}[-\.\s]?\d{2}\b")

# Dicionários de classificação (Macrotemas do Aconchegante)
MACROTEMAS = [
    "Refaturamento & Cobrança",
    "Religação & Multas",
    "Geração Distribuída (GD)",
    "Ouvidoria & Jurídico",
    "Variação de Consumo",
    "Faturamento por Média/Estim.",
    "Entrega da Fatura",
    "Outros"
]

def remove_pii(text: str) -> str:
    if not isinstance(text, str):
        return ""
    t = _CPF_RE.sub("[CPF]", text)
    t = _CNPJ_RE.sub("[CNPJ]", t)
    t = _TELEFONE_RE.sub("[TELEFONE]", t)
    return t.strip()

def infer_macrotema_and_cause(row: pd.Series) -> pd.Series:
    """Aplica RegEx para categorizar a causa raiz e o macrotema (Item 3 da Sprint 21)."""
    assunto = str(row.get("assunto", "")).lower()
    obs = str(row.get("observacao_ordem", "")).lower()
    texto_total = assunto + " " + obs

    macrotema = "Outros"
    causa_raiz = "indefinido"
    is_root_cause = False
    refat = 0.0

    # Regras Refaturamento & Cobrança (Foco Operacional CE)
    if "refatur" in texto_total or "cobrança" in texto_total or "cobranca" in texto_total:
        macrotema = "Refaturamento & Cobrança"
        if "erro" in texto_total and ("leitura" in texto_total or "digita" in texto_total):
            causa_raiz = "digitacao"
            is_root_cause = True
            refat = 1.0
        elif "estim" in texto_total or "media" in texto_total or "média" in texto_total:
            causa_raiz = "leitura_estimada_media"
            macrotema = "Faturamento por Média/Estim."
            is_root_cause = True
        elif "corretivo" in texto_total:
            causa_raiz = "refaturamento_corretivo"
            is_root_cause = True
            refat = 1.0

    # Regras GD
    elif "gd" in texto_total or "geracao" in texto_total or "geração" in texto_total or "microgeracao" in texto_total:
        macrotema = "Geração Distribuída (GD)"
        causa_raiz = "compensacao_gd"

    # Regras Religação & Multas
    elif "religa" in texto_total or "corte" in texto_total or "multa" in texto_total:
        macrotema = "Religação & Multas"

    # Regras Variação de Consumo
    elif "consumo" in texto_total and ("alto" in texto_total or "elevado" in texto_total or "variacao" in texto_total):
        macrotema = "Variação de Consumo"
        causa_raiz = "consumo_elevado_revisao"

    row["macrotema"] = macrotema
    row["causa_raiz_inferida"] = causa_raiz
    row["is_root_cause"] = is_root_cause
    row["ind_refaturamento"] = refat
    return row

def run_pipeline():
    logger.info("Iniciando pipeline Bronze/Silver de Reclamações CE...")
    
    # 1. Ingestão Bronze
    base_dir = Path("DESCRICOES_ENEL")
    excel_files = list(base_dir.glob("reclamacoes_total_*.xlsx"))
    
    if not excel_files:
        logger.warning("Nenhum arquivo 'reclamacoes_total_*.xlsx' encontrado.")
        return

    dfs = []
    for file in excel_files:
        logger.info(f"Lendo {file.name}...")
        df = pd.read_excel(file)
        # Normalização básica de colunas
        df.columns = [str(c).lower().replace(" ", "_").replace(".", "").replace("ç", "c").replace("ã", "a") for c in df.columns]
        dfs.append(df)

    df_bronze = pd.concat(dfs, ignore_index=True)
    logger.info(f"Total de registros Bronze: {len(df_bronze)}")

    # Salva Bronze em formato Parquet
    bronze_path = Path("data/bronze/reclamacoes_ce")
    bronze_path.mkdir(parents=True, exist_ok=True)
    df_bronze.to_parquet(bronze_path / "reclamacoes_ce_raw.parquet", index=False)

    # 2. Transformação Silver (PII & Normalização)
    logger.info("Aplicando transformações Silver (PII e regras de negócio)...")
    df_silver = df_bronze.copy()
    
    # Garantir colunas necessárias existem
    for col in ["observacao_ordem", "devolutiva", "assunto"]:
        if col not in df_silver.columns:
            df_silver[col] = ""
            
    df_silver["observacao_ordem_clean"] = df_silver["observacao_ordem"].apply(remove_pii)
    df_silver["devolutiva_clean"] = df_silver["devolutiva"].apply(remove_pii)

    # 3. Engenharia de Features (Regras Iniciais)
    df_silver = df_silver.apply(infer_macrotema_and_cause, axis=1)

    # 4. Fallback LLM (Camada Silver)
    logger.info("Aplicando fallback LLM em registros não classificados...")
    try:
        from src.common.llm_gateway import build_provider
        from src.rag.config import load_rag_config
        config = load_rag_config()
        provider = build_provider(config)
        
        indefinidos_idx = df_silver[df_silver["causa_raiz_inferida"] == "indefinido"].index
        sample_size = min(len(indefinidos_idx), 50)  # Limite para não onerar CPU no MVP
        
        if sample_size > 0:
            logger.info(f"Inferindo causa-raiz para {sample_size} registros via LLM...")
            for idx in indefinidos_idx[:sample_size]:
                texto = str(df_silver.at[idx, "observacao_ordem_clean"]) + " " + str(df_silver.at[idx, "devolutiva_clean"])
                if len(texto.strip()) < 10:
                    continue
                    
                prompt = (
                    "Classifique a causa-raiz desta reclamação operacional em uma das opções: "
                    "digitacao, refaturamento_corretivo, leitura_estimada_media, medidor_danificado, "
                    "leitura_confirmada_improced, cadastro_inconsistente, erro_processual_faturamento, "
                    "nao_execucao_campo, prazo_fluxo_operacional.\n\n"
                    f"Texto: {texto[:500]}\n\nCausa-raiz:"
                )
                
                try:
                    resp = provider.complete([{"role": "user", "content": prompt}], max_tokens=20)
                    resposta = resp.text.lower()
                    
                    causas_possiveis = [
                        "digitacao", "refaturamento_corretivo", "leitura_estimada_media", 
                        "medidor_danificado", "leitura_confirmada_improced", "cadastro_inconsistente", 
                        "erro_processual_faturamento", "nao_execucao_campo", "prazo_fluxo_operacional"
                    ]
                    
                    for c in causas_possiveis:
                        if c in resposta:
                            df_silver.at[idx, "causa_raiz_inferida"] = c
                            break
                except Exception as e:
                    logger.debug(f"Falha na inferência individual: {e}")
    except Exception as e:
        logger.error(f"Erro ao inicializar provider LLM para fallback: {e}")

    # Salva Silver
    silver_path = Path("data/silver/reclamacoes_ce_tratadas")
    silver_path.mkdir(parents=True, exist_ok=True)
    df_silver.to_parquet(silver_path / "reclamacoes_ce_silver.parquet", index=False)
    logger.info(f"Processamento Silver concluído. Salvo em {silver_path}")

if __name__ == "__main__":
    run_pipeline()