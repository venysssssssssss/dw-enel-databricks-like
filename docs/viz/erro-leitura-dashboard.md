# Dashboard Visual — Erros de Leitura

## Decisão

Para demonstração imediata e exploração visual, o caminho recomendado é **Streamlit**.

Motivos:

- consome diretamente `data/silver/erro_leitura_normalizado.csv` e `data/model_registry/erro_leitura/*`;
- não depende de Trino, Superset, Airflow ou dbt em execução;
- permite filtros interativos por período, região, causa canônica e tópico;
- permite uma narrativa visual mais rica para descoberta de padrões;
- evita exposição de texto livre sensível por design.

Superset continua sendo o destino recomendado para produção, quando a camada Gold estiver publicada em Trino/staging. Nesse cenário, o dataset `infra/config/superset/datasets/erro_leitura_inteligencia_operacional.sql` deve alimentar charts operacionais versionados.

## Visual Story

O app `apps/streamlit/erro_leitura_dashboard.py` organiza a análise em cinco camadas:

- **Ritmo operacional**: evolução mensal por região e Pareto de causas canônicas.
- **Padrões e concentrações**: heatmap região x causa e treemap de tópicos descobertos.
- **Impacto de refaturamento**: taxa de refaturamento por causa, ponderada por volume.
- **Taxonomia descoberta**: tópicos, keywords e amostras mascaradas.
- **Governança analítica**: restrições de PII e regra de uso de `reclamacao_total`.

## Segurança de Dados

O dashboard não mostra:

- `observacao_ordem`;
- `devolutiva`;
- telefone;
- e-mail;
- CEP;
- protocolo;
- identificadores internos;
- instalação em valor bruto.

`instalacao` é transformada em hash apenas para medir reincidência agregada.

## Como Rodar

Instale as dependências opcionais:

```bash
.venv/bin/pip install -e ".[ml,viz]"
```

Gere os dados e artefatos:

```bash
make erro-leitura-normalize
MPLCONFIGDIR=/tmp/matplotlib ENEL_ML_USE_NATIVE_BOOSTERS=false ENEL_MLFLOW_TRACKING_ENABLED=false make erro-leitura-train
```

Abra o dashboard:

```bash
make erro-leitura-dashboard
```

Ou diretamente:

```bash
.venv/bin/streamlit run apps/streamlit/erro_leitura_dashboard.py
```

## Arquitetura

```text
DESCRICOES_ENEL/*.xlsx
  -> data/silver/erro_leitura_normalizado.csv
  -> data/model_registry/erro_leitura/topic_assignments.csv
  -> data/model_registry/erro_leitura/topic_taxonomy.json
  -> src/viz/erro_leitura_dashboard_data.py
  -> apps/streamlit/erro_leitura_dashboard.py
```

O núcleo de agregação fica em `src/viz/erro_leitura_dashboard_data.py` para permitir testes unitários e futura reutilização em API ou export para Superset.
