import os
import json
import httpx
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class GeminiTeacherClient:
    def __init__(self, model: Optional[str] = None):
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.model = model or os.getenv("GEMINI_MODEL_TEACHER", "gemini-1.5-flash") # Doc mentions gemini-3-flash-preview, using 1.5 as safe default if env not set
        self.api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"

    async def generate_content(self, prompt: str, system_instruction: Optional[str] = None) -> str:
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not found in environment")

        payload = {
            "contents": [
                {
                    "parts": [{"text": prompt}]
                }
            ]
        }
        
        if system_instruction:
            payload["system_instruction"] = {
                "parts": [{"text": system_instruction}]
            }

        # Configuração para resposta JSON se o prompt pedir
        if "JSON" in prompt.upper():
            payload["generationConfig"] = {"response_mime_type": "application/json"}

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(self.api_url, json=payload)
            response.raise_for_status()
            data = response.json()
            
            try:
                return data["candidates"][0]["content"]["parts"][0]["text"]
            except (KeyError, IndexError) as e:
                logger.error(f"Error parsing Gemini response: {data}")
                raise e

    async def generate_questions(self, context_json: str, families_budget: Dict[int, int]) -> List[Dict[str, Any]]:
        system_instruction = """
Você é um auditor sênior de produtos analíticos da ENEL Brasil. Sua tarefa é gerar
perguntas de teste para o agente RAG que responde sobre reclamações de erro de
leitura nos estados CE e SP.

Regras:
1. Cada pergunta deve ser passível de resposta com APENAS o contexto fornecido.
2. Distribuição: respeite o orçamento por família fornecido.
3. Português PT-BR, registro profissional, ≤ 18 palavras por pergunta.
4. Para cada pergunta, gere o "gold answer" esperado (3–5 frases) e a lista de
   sources que devem aparecer (paths + section anchors).
5. Para perguntas adversariais, o gold answer é a recusa correta + razão.

Saída: JSON Lines (ou array JSON) com schema:
{ "id": str, "family": int, "question": str, "gold_answer": str, "expected_sources": [str], "difficulty": "easy|medium|hard" }
"""
        prompt = f"Contexto:\n{context_json}\n\nOrçamento por Família:\n{json.dumps(families_budget)}"
        
        response_text = await self.generate_content(prompt, system_instruction=system_instruction)
        
        try:
            return json.loads(response_text)
        except json.JSONDecodeError:
            # Tenta limpar se vier com markdown
            clean_text = response_text.replace("```json", "").replace("```", "").strip()
            return json.loads(clean_text)

    async def critique(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        system_instruction = """
Você é um auditor sênior de qualidade de RAG. Sua tarefa é avaliar a resposta do
agente ENEL comparando com o "gold answer" e as fontes esperadas.

Saída: JSON estrito com o seguinte schema:
{
  "id": str,
  "verdict": "ok | parcial | falha | recusa_correta | recusa_incorreta",
  "factual_correctness": float, (0.0 a 1.0)
  "source_recall": float, (0.0 a 1.0)
  "source_precision": float, (0.0 a 1.0)
  "answer_concision_score": float, (0.0 a 1.0)
  "missed_sources": [str],
  "extra_sources": [str],
  "diagnosis": str,
  "recommended_boosts": [
    { "card_id": str, "delta": float },
    { "doc_path": str, "delta": float }
  ]
}
"""
        prompt = f"Avalie o seguinte payload:\n{json.dumps(payload, ensure_ascii=False)}"
        
        response_text = await self.generate_content(prompt, system_instruction=system_instruction)
        
        try:
            return json.loads(response_text)
        except json.JSONDecodeError:
            clean_text = response_text.replace("```json", "").replace("```", "").strip()
            return json.loads(clean_text)
