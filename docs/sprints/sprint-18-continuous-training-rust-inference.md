# Sprint 18: Retreinamento Contínuo e Inferência Rápida em Rust

## Objetivo
Implementar o ciclo completo de *Continuous Learning* para o RAG, permitindo o retreinamento do modelo de embedding com base no feedback real dos usuários (pesos de acerto/erro). Adicionalmente, garantir que a inferência desse novo modelo na CPU atinja performance extrema utilizando o ONNX Runtime (`ort`) através da biblioteca nativa em Rust (`enel_core`).

## Entregáveis

### 1. Criação do Dataset de Treino a partir do Feedback
Cruzar a telemetria (`data/rag/telemetry.jsonl`) com as avaliações de usuários (`data/rag/feedback.csv`) para montar um dataset composto por tripletos:
- **Query (Pergunta)**
- **Passage Positiva (Acerto)**
- **Passage Negativa (Erro)**

### 2. Fine-tuning do Modelo de Embedding (CPU)
Treinar o modelo de embedding com o dataset de tripletos utilizando `sentence-transformers` (Contrastive Learning / MultipleNegativesRankingLoss), atribuindo pesos de correção aos pares positivos e penalizando os negativos. O resultado será um modelo fine-tunado ajustado perfeitamente aos erros passados do LLM.

### 3. Exportação para ONNX
Exportar o modelo gerado (PyTorch) para o formato ONNX (quantizado opcionalmente), permitindo inferência vetorizada ultrarrápida independente do PyTorch.

O exportador em `scripts/train_embedding_cpu.py` grava um diretório completo em
`data/rag/models/enel-minilm-onnx/`, incluindo `model.onnx`, `tokenizer.json`,
`vocab.txt` e `config.json`. O grafo ONNX expõe:

- `sentence_embedding`: vetor já mean-pooled e normalizado L2, pronto para ChromaDB.
- `last_hidden_state`: saída compatível com runtimes antigos que ainda fazem pooling fora do grafo.

### 4. Inferência em Rust (`enel_core`) via ONNX Runtime
Atualizar a biblioteca Rust do projeto (`enel_core`) com a crate `ort` para rodar o modelo ONNX diretamente na CPU, usando `tokenizers` para pré-processamento. A integração deverá ser exposta de volta ao Python.

`enel_core.OnnxEmbedder` deve preferir `sentence_embedding` quando disponível e
manter fallback para `last_hidden_state`. Em ambientes sem wheel Rust instalada,
`src/rag/ingestion.py` usa `onnxruntime` em Python antes de cair para hashing.

### 5. Atualização do Orquestrador RAG
Alterar os componentes `ingestion.py` e `retriever.py` para utilizarem nativamente a inferência ONNX em Rust quando o modelo estiver disponível.

## Operação

O runtime mantém `RAG_EMBEDDING_MODEL=hashing` como fallback seguro. Para ativar o
modelo ONNX treinado, exporte:

```bash
RAG_EMBEDDING_MODEL=/app/data/rag/models/enel-minilm-onnx
```
