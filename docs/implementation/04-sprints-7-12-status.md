# Status de Implementação — Sprints 07 a 12

## Escopo materializado

O repositório agora contém a espinha dorsal técnica das sprints `07-12`:

- projeto `dbt` com `staging`, `dimensions`, `marts`, `sources`, `macros` e `dag_dbt`;
- assets Superset com configuração, datasets virtuais e saved queries;
- API FastAPI com app factory, autenticação JWT, middlewares, métricas Prometheus, exportação, métricas e scores;
- feature store local com snapshots por `observation_date`, manifests e scripts de materialização;
- builders de features para atraso, inadimplência, metas e anomalias;
- trainers para atraso, inadimplência, metas e anomalias com registry local e tracking compatível com MLflow opcional;
- scoring batch, drift detector, DAGs de ML e stack Docker para MLflow, Prometheus e Grafana.

## Limites atuais

- a implementação é funcional e testável localmente, mas não substitui a validação real com `Trino`, `MinIO`, `MLflow`, `Superset`, `Grafana` e `Airflow` rodando juntos;
- os modelos usam fallback determinístico em `scikit-learn` quando `LightGBM`/`XGBoost`/`MLflow` não estão instalados;
- dashboards Superset e observabilidade foram entregues como assets/configuração, não como instâncias já inicializadas neste ambiente;
- `ruff` e `mypy` continuam fora de conformidade total; a prioridade desta entrega foi funcionamento e rastreabilidade;
- os contratos Gold/API/ML continuam dependentes de validação com stakeholders e dados reais para serem marcados como definitivos.
