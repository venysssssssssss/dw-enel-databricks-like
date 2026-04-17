# RAG Regional Scope (CE/SP)

## Política

O assistente RAG desta base está restrito às regionais:

- Ceará (`CE`)
- São Paulo (`SP`)

Perguntas sobre outras regiões devem retornar recusa educada e explícita.

## Regras de execução

1. `is_out_of_regional_scope(question)` roda antes de retrieval e LLM.
2. Se a pergunta mencionar estados fora de CE/SP (sem CE/SP no texto), ocorre early return com mensagem padrão.
3. `detect_regional_scope(question)` define `region` para o retriever:
   - `CE` -> `where.region in ["CE", "CE+SP"]`
   - `SP` -> `where.region in ["SP", "CE+SP"]`
   - `CE+SP` -> `where.region in ["CE", "SP", "CE+SP"]`
   - `None` -> sem filtro regional (docs/glossário)
4. Para intenção analítica sem região explícita, default é `CE+SP`.

## Metadados obrigatórios de chunks

- `region`: `CE` | `SP` | `CE+SP`
- `scope`: `regional` (cards) ou `global` (docs técnicos)
- `data_source`: origem lógica (`silver.erro_leitura_normalizado` para cards)
- `dataset_version`: hash da versão do DataStore

## Caveat obrigatório de SP

Respostas com métricas de SP devem mencionar viés de cobertura, citando:

- `[fonte: data/silver/erro_leitura_normalizado.csv#data-quality-notes]`
