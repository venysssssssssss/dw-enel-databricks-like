"""Aprendizado contínuo RAG: Telemetria + Feedback -> Conhecimento.

Identifica gaps a partir de feedback negativo e gera relatório.
NOVO: Gera cache dinâmico de perguntas frequentes resolvidas.
"""

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
from datetime import datetime

def load_telemetry(path: Path) -> dict:
    if not path.exists():
        return {}
    
    telemetry = {}
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                data = json.loads(line)
                h = data.get("question_hash")
                if h:
                    telemetry[h] = data
            except:
                pass
    return telemetry

def load_feedback(path: Path) -> list:
    if not path.exists():
        return []
    
    feedbacks = []
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            feedbacks.append(row)
    return feedbacks

def main():
    base_dir = Path(__file__).resolve().parent.parent
    telemetry_path = base_dir / "data/rag/telemetry.jsonl"
    feedback_path = base_dir / "data/rag/feedback.csv"
    output_path = base_dir / "docs/rag/05-continuous-learning-gaps.md"
    dynamic_cache_path = base_dir / "data/rag/dynamic_cache.jsonl"
    
    telemetry = load_telemetry(telemetry_path)
    feedbacks = load_feedback(feedback_path)
    
    down_votes = [f for f in feedbacks if f.get("rating", "").lower() == "down"]
    
    # Separando respostas cacheadas e não cacheadas
    uncached_telemetry = [t for t in telemetry.values() if not t.get("cache_hit")]
    
    # 1. Atualizar Cache Dinâmico (Perguntas Frequentes Resolvidas)
    # Simula extração de respostas boas. Em um cenário real, usaríamos o `texto_gerado`, 
    # mas a telemetria atual salva completion_tokens. Vamos usar uma heurística simples para exemplificar.
    
    dynamic_cache_path.parent.mkdir(parents=True, exist_ok=True)
    existing_cache = set()
    if dynamic_cache_path.exists():
        with open(dynamic_cache_path, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    existing_cache.add(json.loads(line).get("question_preview"))
                except: pass

    new_dynamic_entries = 0
    with open(dynamic_cache_path, "a", encoding="utf-8") as f:
        for t in uncached_telemetry:
            q = t.get("question_preview")
            if q and q not in existing_cache and t.get("completion_tokens", 0) > 20: # Heurística: Resposta razoável
                # No mundo real, a resposta viria de uma curadoria ou de um LLM-as-a-judge forte.
                # Aqui registramos a *intenção* de cache para o orquestrador buscar a resposta real.
                entry = {
                    "question_preview": q,
                    "intent": t.get("intent_class"),
                    "region": t.get("region_detected"),
                    "anchors": t.get("extra", {}).get("sources", []),
                    "added_at": datetime.now().isoformat()
                }
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
                existing_cache.add(q)
                new_dynamic_entries += 1

    
    # 2. Relatório de Gaps
    uncached = [t.get("question_preview") for t in uncached_telemetry]
    top_uncached = Counter(uncached).most_common(10)
    
    lines = [
        "# RAG Continuous Learning: Gaps Identificados",
        f"Gerado em: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n",
        "Este documento consolida o aprendizado contínuo do RAG a partir da telemetria e feedback.",
        "Preencha as respostas para as perguntas abaixo para que sejam indexadas no próximo build do corpus.\n",
        "## 📉 Feedback Negativo (Downvotes)",
    ]
    
    if not down_votes:
        lines.append("*Nenhum feedback negativo registrado.*")
    else:
        for f in down_votes:
            h = f["question_hash"]
            t = telemetry.get(h, {})
            q = t.get("question_preview", "Hash: " + h)
            comment = f.get("comment", "")
            lines.append(f"### Q: {q}")
            lines.append(f"- **Comentário do Usuário**: {comment}")
            lines.append("- **Ação Recomendada**: Revisar os cards de resposta para este tema.")
            lines.append("- **Resposta Curada**: *(Preencha aqui)*\n")
            
    lines.append("\n## 🔄 Top Perguntas Frequentes (Sem Cache)")
    if not top_uncached:
        lines.append("*Nenhuma telemetria disponível.*")
    else:
        for q, count in top_uncached:
            if not q: continue
            lines.append(f"### Q: {q} (Frequência: {count})")
            lines.append("- **Ação Recomendada**: Adicionar a `KNOWN_QUESTION_SEEDS` ou criar card explicativo.")
            lines.append("- **Resposta Curada**: *(Preencha aqui se aplicável)*\n")
            
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
        
    print(f"✅ Aprendizado contínuo gerado em {output_path.relative_to(base_dir)}")
    print(f"✅ {new_dynamic_entries} novas entradas no cache dinâmico.")

if __name__ == "__main__":
    main()
