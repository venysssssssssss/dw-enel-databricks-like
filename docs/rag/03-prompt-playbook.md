# Prompt Playbook v2.0.0

## Objetivo

`src/rag/prompts.py` usa prompt `v2.0.0` por padrão para garantir:

1. Escopo regional CE/SP
2. Resposta exata ao pedido
3. Citações obrigatórias
4. Caveat obrigatório para SP

## Blocos de instrução

- **Escopo regional**: recusa para regiões fora de CE/SP.
- **Exatidão**: sem extrapolar conteúdo não solicitado.
- **Grounding**: usar apenas contexto recuperado.
- **Qualidade de dados**: sempre anotar viés de SP.
- **Few-shots**: 5 exemplos (CE, SP, comparativo, glossário, recusa regional).

## Rollback

Feature flag via ambiente:

```bash
export RAG_PROMPT_VERSION=1.0.0
```

Quando `RAG_PROMPT_VERSION=1.0.0`, o sistema usa o prompt legado.

## Boas práticas de resposta

- Citar no formato `[fonte: caminho#anchor]`.
- Evitar incluir KPIs não solicitados.
- Se dado não estiver no contexto, responder explicitamente que não encontrou.
