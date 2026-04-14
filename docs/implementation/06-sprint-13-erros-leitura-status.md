# Status de Implementação — Sprint 13

## Escopo materializado

A Sprint 13 foi implementada com uma arquitetura ponta a ponta para inteligência operacional de erros de leitura:

- ingestão Bronze unificada de workbooks Excel CE/SP em `src.ingestion.descricoes_enel_ingestor`;
- contrato de fonte em `src/ingestion/config/descricoes_enel.yml`, seguindo o padrão real do projeto;
- normalização Silver com limpeza de texto, deduplicação, extração de entidades e flags de label em `erro_leitura_normalizer.py`;
- modelos Gold/dbt em `dbt/models/marts/erro_leitura`;
- embeddings de texto, topic modeling com sanitização de exemplos, classificador semisupervisionado com taxonomia canônica e detector de anomalias em `src/ml`;
- endpoints FastAPI autenticados em `/api/v1/erros-leitura`;
- asset Superset e DAG Airflow para operação;
- testes unitários cobrindo ingestão, normalização, ML e API.

## Validação local

Validação executável neste ambiente:

- leitura estrutural dos arquivos reais em `DESCRICOES_ENEL/` sem logar textos livres;
- normalização real gerando `data/silver/erro_leitura_normalizado.csv` com 184.690 registros;
- treino local padrão filtrando apenas `_data_type in ('erro_leitura', 'base_n1_sp')`, com 17.057 linhas efetivas;
- taxonomia de tópicos mascarando telefone, e-mail, CEP, protocolo e identificadores internos nos exemplos;
- classificador consolidando variantes de `causa_raiz` para classes canônicas antes do treino;
- dashboard Streamlit local em `apps/streamlit/erro_leitura_dashboard.py`, com camada de agregação testável em `src/viz/erro_leitura_dashboard_data.py`;
- testes unitários com dados sintéticos;
- smoke integration preparado para `DESCRICOES_ENEL/` quando o diretório existir.

## Limites atuais

- BERTopic, sentence-transformers, UMAP e HDBSCAN foram adicionados como dependências opcionais de ML, mas o caminho padrão local usa fallback `scikit-learn` para manter execução CPU-only e estável;
- o baseline local atual ficou em `macro_f1=0.2743` usando rótulos fracos/canônicos; métrica produtiva exige amostra rotulada por especialista;
- coerência de tópicos e precisão de anomalias ainda dependem de validação humana e dados rotulados reais;
- Gold/dbt, API com Trino real, Superset e Airflow ainda precisam de execução no ambiente produtivo ou staging equivalente;
- a cobertura operacional exigida pela Definition of Done só fecha após 3 DAG runs reais e revisão humana dos tópicos/anomalias.
