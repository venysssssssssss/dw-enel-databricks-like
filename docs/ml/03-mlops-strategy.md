# Estratégia de MLOps

## Ciclo de Vida do Modelo

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  Experiment  │───►│  Candidate   │───►│  Production  │───►│  Archived    │
│  (Training)  │    │  (Staging)   │    │  (Scoring)   │    │  (Retired)   │
└──────────────┘    └──────────────┘    └──────────────┘    └──────────────┘
       │                   │                   │                    │
       │ MLflow tracking   │ Validação         │ Batch scoring      │ Drift detectado
       │ Métricas          │ A/B test          │ Monitoramento      │ Modelo substituído
       │ Artefatos         │ Aprovação         │ Alertas            │
```

## MLflow — Organização

### Experiments

```
MLflow Experiments:
├── enel-atraso-entrega/
│   ├── run-2026-03-25-v1 (LightGBM baseline)
│   ├── run-2026-03-26-v2 (LightGBM tuned)
│   └── run-2026-03-27-v3 (LightGBM + novas features)
├── enel-inadimplencia/
│   ├── run-2026-04-01-v1 (XGBoost baseline)
│   └── ...
├── enel-metas/
│   └── ...
└── enel-anomalias/
    └── ...
```

### Artefatos por Run

Cada run do MLflow registra:

```python
import mlflow

with mlflow.start_run(run_name=f"lgb-atraso-{date}"):
    # 1. Parâmetros
    mlflow.log_params(model_params)
    mlflow.log_param("feature_count", len(features))
    mlflow.log_param("train_size", len(X_train))
    mlflow.log_param("train_date_range", f"{train_start} to {train_end}")

    # 2. Métricas
    mlflow.log_metrics({
        "auc_roc": auc,
        "recall_atraso": recall,
        "precision_atraso": precision,
        "f1_atraso": f1,
        "mae_dias": mae,
    })

    # 3. Modelo
    mlflow.lightgbm.log_model(model, "model")

    # 4. Artefatos de explicabilidade
    mlflow.log_artifact("shap_summary.png")
    mlflow.log_artifact("feature_importance.csv")
    mlflow.log_artifact("confusion_matrix.png")
    mlflow.log_artifact("calibration_curve.png")

    # 5. Feature manifest
    mlflow.log_artifact("feature_manifest.json")

    # 6. Dataset info
    mlflow.log_input(mlflow.data.from_pandas(X_train), context="training")
```

### Model Registry

```python
# Promoção para produção
client = mlflow.MlflowClient()
client.transition_model_version_stage(
    name="enel-atraso-entrega",
    version=3,
    stage="Production",
    archive_existing_versions=True,
)
```

## Pipeline de Scoring Batch

### DAG Airflow: `ml_scoring_daily`

```python
# Executa diariamente após feature engineering
dag_ml_scoring = DAG(
    dag_id='ml_scoring_daily',
    schedule_interval='0 8 * * *',  # 8h diário
    depends_on_past=False,
)

# Tasks sequenciais
load_features >> load_model >> predict >> validate_scores >> publish_scores
```

### Fluxo de Scoring

```
1. Carregar features do dia (MinIO)
2. Carregar modelo Production do MLflow Registry
3. Gerar predições
4. Calcular SHAP values (top 3 por predição)
5. Validar scores (distribuição, nulos, range)
6. Publicar no MinIO (gold/ml_scores/)
7. Registrar métricas de scoring no MLflow
```

### Schema de Output (Scores)

```sql
CREATE TABLE gold.score_atraso_entrega (
    cod_nota            BIGINT NOT NULL,
    data_scoring        DATE NOT NULL,
    score_atraso        DOUBLE NOT NULL,      -- probabilidade 0-1
    classe_predita      STRING NOT NULL,       -- 'ATRASO' / 'NO_PRAZO'
    dias_atraso_pred    DOUBLE,                -- dias estimados de atraso
    confianca           DOUBLE NOT NULL,       -- confiança da predição
    top_feature_1       STRING NOT NULL,       -- feature mais importante
    top_feature_1_val   DOUBLE NOT NULL,       -- SHAP value
    top_feature_2       STRING NOT NULL,
    top_feature_2_val   DOUBLE NOT NULL,
    top_feature_3       STRING NOT NULL,
    top_feature_3_val   DOUBLE NOT NULL,
    model_version       STRING NOT NULL,       -- versão do modelo MLflow
    _run_id             STRING NOT NULL,
    _scored_at          TIMESTAMP NOT NULL
)
PARTITIONED BY (data_scoring)
```

## Monitoramento de Drift

### Tipos de Drift Monitorados

| Tipo | O que mede | Método | Threshold |
|---|---|---|---|
| Feature drift | Mudança na distribuição das features | PSI (Population Stability Index) | PSI > 0.2 → alerta |
| Prediction drift | Mudança na distribuição dos scores | PSI + KS test | PSI > 0.2 |
| Concept drift | Degradação da performance real | Métricas vs baseline | AUC drop > 5% |
| Data quality drift | Aumento de nulos, outliers | Taxa de nulos, range | Nulos > 2x baseline |

### Cálculo de PSI

```python
def calculate_psi(expected, actual, bins=10):
    """Population Stability Index entre distribuição esperada e atual."""
    breakpoints = np.linspace(0, 1, bins + 1)

    expected_pcts = np.histogram(expected, breakpoints)[0] / len(expected)
    actual_pcts = np.histogram(actual, breakpoints)[0] / len(actual)

    # Evitar log(0)
    expected_pcts = np.clip(expected_pcts, 0.001, None)
    actual_pcts = np.clip(actual_pcts, 0.001, None)

    psi = np.sum((actual_pcts - expected_pcts) * np.log(actual_pcts / expected_pcts))
    return psi

# Interpretação:
# PSI < 0.1  → Estável
# PSI 0.1-0.2 → Mudança moderada, investigar
# PSI > 0.2  → Mudança significativa, retreinar
```

### DAG de Monitoramento

```python
dag_ml_monitoring = DAG(
    dag_id='ml_monitoring_daily',
    schedule_interval='0 10 * * *',  # 10h, após scoring
)

# Tasks
check_feature_drift >> check_prediction_drift >> check_performance >> generate_report >> alert_if_needed
```

### Alertas

```python
# Critérios de alerta
alerts = {
    'DRIFT_WARNING': 'PSI entre 0.1 e 0.2 em qualquer feature',
    'DRIFT_CRITICAL': 'PSI > 0.2 em feature importante',
    'PERFORMANCE_DROP': 'AUC caiu mais de 5% vs baseline',
    'DATA_QUALITY': 'Taxa de nulos > 2x do esperado',
    'SCORING_FAILURE': 'Pipeline de scoring falhou',
}
```

## Retreinamento

### Critérios para Retreinar

1. **Automático (scheduled)**: Retreinar mensalmente com dados mais recentes
2. **Por drift**: Quando PSI > 0.2 em feature crítica
3. **Por performance**: Quando métricas caem abaixo do threshold
4. **Por mudança de negócio**: Novas regras, novas fontes, novo domínio

### Pipeline de Retreinamento

```
1. Extrair dados de treino atualizados (últimos 12 meses)
2. Gerar features com pipeline atual
3. Treinar modelo com mesmos hiperparâmetros
4. Avaliar com TimeSeriesSplit
5. Comparar com modelo em produção
6. SE melhor → promover para Staging
7. Validação manual/automática
8. SE aprovado → promover para Production
```

### Janelas de Treino

| Modelo | Janela de Treino | Janela de Validação | Retreino |
|---|---|---|---|
| Atraso | 6-12 meses | Último mês | Mensal |
| Inadimplência | 12-18 meses | Últimos 2 meses | Mensal |
| Metas | 6-12 meses | Último mês | Mensal |
| Anomalias | 3-6 meses (rolling) | Contínuo | Quinzenal |
