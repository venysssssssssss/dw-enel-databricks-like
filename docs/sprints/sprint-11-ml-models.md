# Sprint 11 — Modelos Preditivos: Training & Validation

**Fase**: 4 — ML & Operação Assistida
**Duração**: 2 semanas
**Objetivo**: Treinar, validar e registrar no MLflow os 4 modelos preditivos — atraso, inadimplência, metas e anomalias — com interpretabilidade SHAP e validação temporal.

**Pré-requisito**: Sprint 10 completa (Features materializados, MLflow operacional)

---

## Backlog da Sprint

### US-056: Modelo — Predição de Atraso (LightGBM)
**Prioridade**: P0
**Story Points**: 8

**Tarefas**:

1. **Criar `src/ml/models/atraso_model.py`**:
   ```python
   """Treinamento e avaliação do modelo de atraso."""

   class AtrasoModelTrainer:
       def __init__(self, feature_store: FeatureStore, mlflow_uri: str):
           self.feature_store = feature_store
           mlflow.set_tracking_uri(mlflow_uri)
           mlflow.set_experiment("enel-atraso-entrega")

       def train(self, train_dates: tuple[date, date], test_date: date) -> str:
           """Treina modelo de atraso e registra no MLflow."""

           # 1. Carregar features
           df_features = self._load_training_data(train_dates, test_date)

           # 2. Preparar dados
           feature_cols = [c for c in df_features.columns
                          if not c.startswith(('target_', '_', 'cod_nota'))]
           categorical_cols = ['tipo_servico', 'classificacao_acf_asf',
                              'dia_semana_criacao', 'dia_semana_previsto',
                              'cod_distribuidora', 'cod_ut', 'cod_co']

           X_train, X_test, y_train, y_test = self._temporal_split(
               df_features, feature_cols, 'target_flag_atraso', test_date
           )

           # 3. Treinar com MLflow tracking
           with mlflow.start_run(run_name=f"lgb-atraso-{date.today()}"):
               # Parâmetros
               params = {
                   'objective': 'binary',
                   'metric': ['binary_logloss', 'auc'],
                   'boosting_type': 'gbdt',
                   'num_leaves': 63,
                   'max_depth': 8,
                   'learning_rate': 0.05,
                   'feature_fraction': 0.8,
                   'bagging_fraction': 0.8,
                   'bagging_freq': 5,
                   'min_child_samples': 50,
                   'n_estimators': 500,
                   'device_type': 'cpu',
                   'num_threads': 4,
                   'is_unbalance': True,
                   'verbose': -1,
               }
               mlflow.log_params(params)

               # Treinar
               train_data = lgb.Dataset(
                   X_train, y_train,
                   categorical_feature=categorical_cols,
               )
               valid_data = lgb.Dataset(
                   X_test, y_test,
                   categorical_feature=categorical_cols,
                   reference=train_data,
               )

               model = lgb.train(
                   params,
                   train_data,
                   valid_sets=[valid_data],
                   callbacks=[
                       lgb.early_stopping(30),
                       lgb.log_evaluation(50),
                   ],
               )

               # 4. Avaliar
               y_pred_proba = model.predict(X_test)
               y_pred = (y_pred_proba > 0.5).astype(int)

               metrics = {
                   'auc_roc': roc_auc_score(y_test, y_pred_proba),
                   'recall_atraso': recall_score(y_test, y_pred),
                   'precision_atraso': precision_score(y_test, y_pred),
                   'f1_atraso': f1_score(y_test, y_pred),
                   'accuracy': accuracy_score(y_test, y_pred),
                   'train_size': len(X_train),
                   'test_size': len(X_test),
                   'positive_rate_train': y_train.mean(),
                   'positive_rate_test': y_test.mean(),
               }
               mlflow.log_metrics(metrics)

               # 5. SHAP
               explainer = shap.TreeExplainer(model)
               shap_values = explainer.shap_values(X_test[:1000])  # amostra para performance

               # Salvar plots
               fig_summary = shap.summary_plot(shap_values[1], X_test[:1000],
                                               show=False)
               mlflow.log_figure(fig_summary, "shap_summary.png")

               fig_importance = self._plot_feature_importance(model, feature_cols)
               mlflow.log_figure(fig_importance, "feature_importance.png")

               fig_cm = self._plot_confusion_matrix(y_test, y_pred)
               mlflow.log_figure(fig_cm, "confusion_matrix.png")

               # 6. Registrar modelo
               mlflow.lightgbm.log_model(
                   model, "model",
                   registered_model_name="enel-atraso-entrega",
               )

               # 7. Validar thresholds mínimos
               self._validate_thresholds(metrics)

               return mlflow.active_run().info.run_id

       def _temporal_split(self, df, features, target, test_date):
           """Split temporal — tudo antes de test_date é treino."""
           train_mask = df['data_criacao'] < test_date
           test_mask = df['data_criacao'] >= test_date

           X_train = df.loc[train_mask, features]
           X_test = df.loc[test_mask, features]
           y_train = df.loc[train_mask, target]
           y_test = df.loc[test_mask, target]
           return X_train, X_test, y_train, y_test

       def _validate_thresholds(self, metrics):
           """Valida que métricas atendem mínimos aceitáveis."""
           thresholds = {
               'auc_roc': 0.75,
               'recall_atraso': 0.70,
               'f1_atraso': 0.58,
           }
           for metric, min_val in thresholds.items():
               if metrics[metric] < min_val:
                   self.logger.warning(
                       "metric_below_threshold",
                       metric=metric,
                       value=metrics[metric],
                       threshold=min_val,
                   )
   ```

2. **Cross-validation temporal**:
   ```python
   def cross_validate_temporal(self, df, feature_cols, target, n_splits=5):
       """TimeSeriesSplit com gap de 7 dias."""
       tscv = TimeSeriesSplit(n_splits=n_splits, gap=7)
       scores = []
       for fold, (train_idx, test_idx) in enumerate(tscv.split(df)):
           # treina e avalia cada fold
           ...
           scores.append(fold_metrics)
       return pd.DataFrame(scores).describe()
   ```

**Critério de aceite**:
- Modelo treinado e registrado no MLflow
- AUC ≥ 0.75 (em dados de teste temporal)
- SHAP summary e feature importance gerados
- Cross-validation temporal com 5 folds
- Modelo funciona em CPU com < 6GB RAM

---

### US-057: Modelo — Predição de Inadimplência (XGBoost)
**Prioridade**: P0
**Story Points**: 5

**Tarefas**:

1. **Criar `src/ml/models/inadimplencia_model.py`**:
   - Mesmo padrão do atraso, mas com XGBoost
   - `scale_pos_weight` para desbalanceamento
   - Calibração posterior com `CalibratedClassifierCV`
   - Segmentação de risco no output (ALTO/MEDIO/BAIXO/MINIMO)
   - Métricas: AUC, Brier Score, KS Statistic, Recall@Top20%

2. **Calibração de probabilidades**:
   ```python
   from sklearn.calibration import CalibratedClassifierCV, calibration_curve

   # Calibrar
   calibrated = CalibratedClassifierCV(model, method='isotonic', cv=5)
   calibrated.fit(X_train, y_train)

   # Validar calibração
   prob_true, prob_pred = calibration_curve(y_test, calibrated.predict_proba(X_test)[:, 1], n_bins=10)
   # Plot e salvar no MLflow
   ```

**Critério de aceite**:
- AUC ≥ 0.78
- Brier Score ≤ 0.15
- Probabilidades calibradas (curva de calibração próxima da diagonal)
- Segmentação de risco funcional

---

### US-058: Modelo — Projeção de Meta (LightGBM + Logistic Regression)
**Prioridade**: P1
**Story Points**: 5

**Tarefas**:

1. **Criar `src/ml/models/metas_model.py`**:
   - LightGBM para regressão (% atingimento projetado)
   - Logistic Regression para classificação interpretável
   - Ensemble: média ponderada (0.6 LGB + 0.4 LR)
   - Métricas: RMSE, MAE, Accuracy

2. **Output interpretável para negócio**:
   ```python
   def explain_prediction(self, row):
       """Gera explicação textual para stakeholders."""
       top_features = self._get_top_shap(row, n=3)
       return {
           "projecao_pct": round(prediction, 1),
           "status": "EM_RISCO" if prediction < 90 else "NO_CAMINHO",
           "explicacao": [
               f"{f['name']}: {f['direction']} ({f['impact']:.1f}%)"
               for f in top_features
           ]
       }
   ```

**Critério de aceite**:
- RMSE ≤ 8% no atingimento projetado
- Explicação textual gerada por predição
- Ensemble melhora vs modelos individuais

---

### US-059: Modelo — Detecção de Anomalias (Isolation Forest)
**Prioridade**: P1
**Story Points**: 5

**Tarefas**:

1. **Criar `src/ml/models/anomalia_model.py`**:
   ```python
   class AnomaliaDetector:
       """Detecção de anomalias com abordagem híbrida."""

       def __init__(self):
           self.iso_forest = IsolationForest(
               n_estimators=200,
               contamination=0.05,
               max_features=0.8,
               n_jobs=4,
               random_state=42,
           )

       def detect(self, df: pd.DataFrame) -> pd.DataFrame:
           """Detecta anomalias com Isolation Forest + Z-Score."""
           # Isolation Forest para anomalias multivariadas
           numeric_cols = df.select_dtypes(include=[np.number]).columns
           df['anomaly_score_if'] = self.iso_forest.decision_function(df[numeric_cols])
           df['is_anomaly_if'] = self.iso_forest.predict(df[numeric_cols]) == -1

           # Z-Score para métricas individuais
           for col in ['taxa_atraso_base_7d', 'efetividade_base_7d', 'volume_notas_base_7d']:
               z = stats.zscore(df[col].dropna())
               df[f'zscore_{col}'] = z
               df[f'is_anomaly_zscore_{col}'] = abs(z) > 3.0

           # Score combinado
           df['anomaly_combined'] = (
               df['is_anomaly_if'].astype(int) +
               df[[c for c in df.columns if c.startswith('is_anomaly_zscore_')]].sum(axis=1)
           )
           df['is_anomaly'] = df['anomaly_combined'] >= 1

           return df
   ```

2. **Cenários de detecção** (conforme `docs/ml/01-model-selection.md`):
   - Base com atraso atípico
   - Colaborador com produtividade anômala
   - Pico/queda de volume de notas

**Critério de aceite**:
- Anomalias detectadas em dados de amostra
- Score de anomalia atribuído a cada registro
- Alertas gerados para anomalias confirmadas
- Nenhum label necessário (unsupervised)

---

### US-060: Baseline Models e Comparação
**Prioridade**: P0
**Story Points**: 3

**Tarefas**:

1. **Criar baselines simples para cada caso de uso**:
   ```python
   # Baseline atraso: taxa histórica por base
   baseline_atraso = df.groupby('cod_base')['target_flag_atraso'].mean()
   # Prediz "atraso" se taxa da base > 50%

   # Baseline inadimplência: taxa histórica por UC
   baseline_inadimplencia = df.groupby('cod_uc')['target_flag_inadimplente'].mean()

   # Baseline metas: projeção linear
   baseline_metas = df['pct_realizado_atual'] / df['pct_dias_uteis_decorridos'] * 100
   ```

2. **Comparar ML vs Baseline em cada métrica**
3. **Registrar baselines no MLflow** para tracking

**Critério de aceite**:
- Baseline registrado no MLflow para cada caso de uso
- Modelo ML supera baseline em todas as métricas
- Delta ML vs Baseline documentado

---

## Entregáveis da Sprint

| Entregável | Status |
|---|---|
| Modelo Atraso (LightGBM) treinado e registrado | |
| Modelo Inadimplência (XGBoost calibrado) treinado e registrado | |
| Modelo Metas (LightGBM + LR ensemble) treinado e registrado | |
| Modelo Anomalias (Isolation Forest) treinado | |
| Baselines para comparação | |
| SHAP explanations para todos os modelos supervisionados | |
| Cross-validation temporal (5 folds) | |
| Feature importance plots | |
| Métricas registradas no MLflow | |

## Verificação

```bash
# 1. Acessar MLflow UI
open http://localhost:5000

# 2. Verificar experiments
# - Cada experiment deve ter pelo menos 1 run
# - Métricas acima dos thresholds
# - Artefatos (SHAP, feature importance, confusion matrix)

# 3. Testar predição
python -c "
from src.ml.models.atraso_model import AtrasoModelTrainer
trainer = AtrasoModelTrainer(feature_store, 'http://localhost:5000')
# Load model and predict sample
import mlflow
model = mlflow.lightgbm.load_model('models:/enel-atraso-entrega/latest')
print(model.predict(X_sample[:5]))
"

# 4. Verificar memória durante treinamento
# Deve ficar < 8GB total (modelo + features + sistema)
```
