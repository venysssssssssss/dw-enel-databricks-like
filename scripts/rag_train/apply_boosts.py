import argparse
import json
import logging
from pathlib import Path
from collections import defaultdict

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

def apply_boosts(round_num: str):
    logger.info(f"Aplicando boosts da round {round_num}")
    
    round_dir = Path(f"data/rag_train/round-{round_num}")
    critiques_file = round_dir / "critiques.jsonl"
    boosts_output = round_dir / "boosts.json"
    active_boosts_file = Path("data/rag_train/active_boosts.json")
    
    if not critiques_file.exists():
        logger.error(f"Arquivo de críticas não encontrado: {critiques_file}")
        return

    # 1. Agregar recommended_boosts
    aggregated_boosts = defaultdict(float)
    
    count = 0
    with open(critiques_file, "r", encoding="utf-8") as f:
        for line in f:
            critique = json.loads(line)
            for boost in critique.get("recommended_boosts", []):
                target = boost.get("card_id") or boost.get("doc_path")
                if target:
                    aggregated_boosts[target] += boost.get("delta", 0.0)
            count += 1
            
    # 2. Carregar boosts atuais se existirem
    current_boosts = {}
    if active_boosts_file.exists():
        with open(active_boosts_file, "r", encoding="utf-8") as f:
            current_boosts = json.load(f)
            
    # 3. Aplicar novos boosts com clip(0.5, 2.0)
    new_boosts = current_boosts.copy()
    for target, delta in aggregated_boosts.items():
        # Delta médio ou apenas soma? O doc diz "somando deltas".
        # Vamos somar e aplicar o clip.
        current_val = new_boosts.get(target, 1.0)
        new_val = current_val + delta
        new_boosts[target] = max(0.5, min(2.0, new_val))
        
    # 4. Salvar versão da round
    with open(boosts_output, "w", encoding="utf-8") as f:
        json.dump(new_boosts, f, indent=2, ensure_ascii=False)
        
    # 5. Atualizar active_boosts.json
    active_boosts_file.parent.mkdir(parents=True, exist_ok=True)
    with open(active_boosts_file, "w", encoding="utf-8") as f:
        json.dump(new_boosts, f, indent=2, ensure_ascii=False)
        
    logger.info(f"Sucesso: {len(aggregated_boosts)} boosts agregados a partir de {count} críticas.")
    logger.info(f"Boosts ativos salvos em {active_boosts_file}")

def main():
    parser = argparse.ArgumentParser(description="Apply boosts from critiques")
    parser.add_argument("--round", type=str, required=True, help="Número da round")
    args = parser.parse_args()
    
    apply_boosts(args.round)

if __name__ == "__main__":
    main()
