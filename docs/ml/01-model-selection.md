# Seleção de Modelos de Machine Learning

## Restrições de Hardware

| Restrição | Impacto |
|---|---|
| CPU-only (Intel Iris Xe = GPU integrada, inaproveitável para ML) | Sem CUDA, sem deep learning prático |
| 16GB RAM (6-8GB disponíveis para ML) | Modelos devem ser memory-efficient |
| 4 cores / 8 threads | Paralelismo limitado |

**Consequência**: Modelos baseados em árvore (gradient boosting) são ideais — rápidos em CPU, eficientes em memória, excelentes para dados tabulares.

---

## Caso de Uso 1: Predição de Atraso de Entrega

### Natureza do Problema
- **Tipo**: Classificação binária (atraso SIM/NÃO) + Regressão (dias de atraso)
- **Target**: `flag_atraso` (binário) e `dias_atraso` (contínuo)
- **Granularidade**: 1 predição por nota operacional

### Modelo Selecionado: LightGBM

| Critério | LightGBM | XGBoost | CatBoost | Random Forest |
|---|---|---|---|---|
| Velocidade CPU | ★★★★★ | ★★★☆☆ | ★★★★☆ | ★★★☆☆ |
| Memória | ★★★★★ | ★★★☆☆ | ★★★★☆ | ★★☆☆☆ |
| Categóricas nativas | ★★★★★ | ★★☆☆☆ | ★★★★★ | ★☆☆☆☆ |
| Handling de nulos | ★★★★★ | ★★★★★ | ★★★★☆ | ★☆☆☆☆ |
| Interpretabilidade | ★★★★☆ | ★★★★☆ | ★★★☆☆ | ★★★★★ |
| Desempenho tabular | ★★★★★ | ★★★★★ | ★★★★★ | ★★★☆☆ |

**Justificativa**: LightGBM é o mais rápido em CPU, usa menos memória (histogram-based), suporta features categóricas nativamente (crítico para distribuidora, UT, CO, tipo_servico) e escala bem com volume moderado.

### Configuração Recomendada

```python
import lightgbm as lgb

# Classificação (atraso SIM/NÃO)
clf_params = {
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
    'early_stopping_rounds': 30,
    'device_type': 'cpu',
    'num_threads': 4,
    'verbose': -1,
    'is_unbalance': True,  # classes desbalanceadas (mais "no prazo" que "atrasado")
    'categorical_feature': ['cod_distribuidora', 'cod_ut', 'cod_co', 'tipo_servico',
                            'classificacao_acf_asf', 'dia_semana']
}

# Regressão (dias de atraso)
reg_params = {
    'objective': 'regression',
    'metric': ['rmse', 'mae'],
    'boosting_type': 'gbdt',
    'num_leaves': 63,
    'max_depth': 8,
    'learning_rate': 0.05,
    'feature_fraction': 0.8,
    'bagging_fraction': 0.8,
    'min_child_samples': 50,
    'n_estimators': 500,
    'early_stopping_rounds': 30,
    'device_type': 'cpu',
    'num_threads': 4,
}
```

### Métricas de Avaliação

| Métrica | Threshold Mínimo | Justificativa |
|---|---|---|
| AUC-ROC | ≥ 0.75 | Discriminação entre atrasado/no prazo |
| Recall (atraso) | ≥ 0.70 | Preferível capturar mais atrasos (falso negativo é caro) |
| Precision (atraso) | ≥ 0.50 | Tolerância a falsos positivos (melhor prevenir) |
| F1 (atraso) | ≥ 0.58 | Balanço entre recall e precision |
| MAE (dias) | ≤ 3 dias | Para regressão de dias de atraso |

### Baseline

Antes do modelo, calcular baselines simples:
- **Baseline 1**: Taxa histórica de atraso por base/CO → predizer "atraso" se taxa > 50%
- **Baseline 2**: Regra: se nota ACF_A com mais de 2 dias para vencimento → "sem atraso"

---

## Caso de Uso 2: Predição de Não Pagamento

### Natureza do Problema
- **Tipo**: Classificação binária (paga / não paga) com probabilidade calibrada
- **Target**: `flag_inadimplente` (binário)
- **Granularidade**: 1 predição por fatura emitida

### Modelo Selecionado: XGBoost

**Justificativa**: XGBoost oferece melhor calibração de probabilidades out-of-the-box, critical para segmentação de risco. O `scale_pos_weight` lida bem com desbalanceamento. A saída probabilística é mais confiável que LightGBM para este caso onde a **probabilidade** importa mais que a **classe**.

### Configuração Recomendada

```python
import xgboost as xgb

params = {
    'objective': 'binary:logistic',
    'eval_metric': ['logloss', 'auc'],
    'tree_method': 'hist',        # mais eficiente em CPU
    'max_depth': 6,
    'learning_rate': 0.03,
    'subsample': 0.8,
    'colsample_bytree': 0.8,
    'min_child_weight': 50,
    'n_estimators': 800,
    'early_stopping_rounds': 50,
    'scale_pos_weight': ratio_negativo_positivo,  # calculado do treino
    'nthread': 4,
    'verbosity': 0,
}

# Calibração posterior com CalibratedClassifierCV
from sklearn.calibration import CalibratedClassifierCV
calibrated_model = CalibratedClassifierCV(model, method='isotonic', cv=5)
```

### Segmentação de Risco (output)

```python
def segmentar_risco(probabilidade):
    if probabilidade >= 0.70:
        return 'ALTO'       # Ação imediata de cobrança
    elif probabilidade >= 0.40:
        return 'MEDIO'      # Monitoramento intensificado
    elif probabilidade >= 0.15:
        return 'BAIXO'      # Acompanhamento padrão
    else:
        return 'MINIMO'     # Sem ação especial
```

### Métricas de Avaliação

| Métrica | Threshold | Justificativa |
|---|---|---|
| AUC-ROC | ≥ 0.78 | Discriminação de risco |
| Brier Score | ≤ 0.15 | Calibração de probabilidades |
| KS Statistic | ≥ 0.40 | Separação entre classes |
| Recall@Top20% | ≥ 0.50 | Top 20% de risco deve capturar 50%+ dos inadimplentes |

---

## Caso de Uso 3: Projeção de Meta Não Atingida

### Natureza do Problema
- **Tipo**: Regressão (% de atingimento projetado) + Classificação (atingirá/não atingirá)
- **Target**: `pct_atingimento_final` (contínuo) e `flag_meta_atingida` (binário)
- **Granularidade**: 1 predição por (meta × base × mês)

### Modelo Selecionado: LightGBM (Regressão) + Logistic Regression (Ensemble)

**Justificativa**: LightGBM para capturar padrões não-lineares + Logistic Regression como modelo interpretável para stakeholders de negócio. O ensemble combina a capacidade preditiva do LightGBM com a explicabilidade da regressão logística.

### Configuração Recomendada

```python
# Modelo 1: LightGBM para projeção numérica
lgb_params = {
    'objective': 'regression',
    'metric': ['rmse', 'mae'],
    'num_leaves': 31,
    'max_depth': 6,
    'learning_rate': 0.05,
    'feature_fraction': 0.7,
    'n_estimators': 300,
    'device_type': 'cpu',
    'num_threads': 4,
}

# Modelo 2: Logistic Regression para classificação interpretável
from sklearn.linear_model import LogisticRegression
lr_params = {
    'penalty': 'l1',              # Feature selection automática
    'C': 1.0,
    'solver': 'saga',
    'max_iter': 1000,
    'class_weight': 'balanced',
}

# Ensemble: média ponderada das probabilidades
# peso_lgb = 0.6, peso_lr = 0.4
```

### Feature Engineering Temporal

Este caso exige features que capturam **progresso dentro do mês**:

```python
# Features de momentum
features_temporais = {
    'dia_do_mes': 'dia atual no mês',
    'pct_dias_uteis_decorridos': 'fração do mês útil que já passou',
    'pct_realizado_atual': 'realizado / meta até agora',
    'taxa_diaria_necessaria': '(meta - realizado) / dias_uteis_restantes',
    'taxa_diaria_atual': 'realizado / dias_uteis_decorridos',
    'gap_velocidade': 'taxa_diaria_atual - taxa_diaria_necessaria',
    'tendencia_7d': 'slope do realizado nos últimos 7 dias',
    'volatilidade_7d': 'std do realizado diário nos últimos 7 dias',
    'mesmo_ponto_mes_anterior': 'pct_realizado neste dia do mês anterior',
    'delta_vs_mes_anterior': 'pct_atual - pct_mesmo_ponto_mes_anterior',
}
```

### Métricas de Avaliação

| Métrica | Threshold |
|---|---|
| RMSE (% atingimento) | ≤ 8% |
| MAE (% atingimento) | ≤ 5% |
| Accuracy (atingiu/não) | ≥ 0.80 |
| Recall (não atingiu) | ≥ 0.75 |

---

## Caso de Uso 4: Detecção de Anomalias

### Natureza do Problema
- **Tipo**: Detecção de anomalias (unsupervised → semi-supervised)
- **Sem target explícito**: anomalias são padrões fora da distribuição normal
- **Granularidade**: Múltiplas (por nota, por base/dia, por colaborador/dia)

### Modelo Selecionado: Isolation Forest + Z-Score Statistical

**Justificativa**: Isolation Forest é o modelo de anomalia mais eficiente em CPU/memória, não precisa de labels (unsupervised), e escala bem. Z-Score complementa para métricas com distribuição conhecida.

### Abordagem Híbrida

```python
from sklearn.ensemble import IsolationForest
from scipy import stats

# Modelo 1: Isolation Forest para anomalias multivariadas
iso_forest = IsolationForest(
    n_estimators=200,
    max_samples='auto',
    contamination=0.05,      # estimativa de 5% de anomalias
    max_features=0.8,
    n_jobs=4,
    random_state=42,
)

# Modelo 2: Z-Score para anomalias univariadas
def detect_zscore_anomaly(series, threshold=3.0):
    z_scores = stats.zscore(series, nan_policy='omit')
    return abs(z_scores) > threshold

# Modelo 3: IQR para métricas com distribuição assimétrica
def detect_iqr_anomaly(series, factor=1.5):
    Q1 = series.quantile(0.25)
    Q3 = series.quantile(0.75)
    IQR = Q3 - Q1
    lower = Q1 - factor * IQR
    upper = Q3 + factor * IQR
    return (series < lower) | (series > upper)
```

### Cenários de Detecção

| Cenário | Features | Método | Saída |
|---|---|---|---|
| Base com atraso atípico | taxa_atraso, media_historica_base | Z-Score | Alert se desvio > 2σ |
| Colaborador com produtividade anômala | notas_dia, media_equipe, media_historica | IQR | Alert se fora do IQR |
| Padrão geográfico incomum | lat/lon de execuções, distância média | Isolation Forest | Cluster de anomalias |
| Pico/queda de notas | volume_diario, sazonalidade | Z-Score + trend | Alert se residual > 3σ |
| Efetividade fora do padrão | efetividade_base vs pares | IQR | Bases outliers |

### Métricas de Avaliação (Anomalias)

Como não há labels inicialmente:

| Abordagem | Métrica |
|---|---|
| Cobertura | % de alertas revisados pela operação |
| Precisão estimada | % de alertas confirmados como reais |
| Estabilidade | Variância no número de alertas dia a dia |
| Feedback loop | Após 3 meses, usar confirmações como labels → semi-supervised |

---

## Tabela Resumo — Modelos Selecionados

| Caso de Uso | Modelo Principal | Modelo Auxiliar | Tipo | Output |
|---|---|---|---|---|
| Atraso de Entrega | LightGBM | Baseline por regra | Classificação + Regressão | Score 0-1 + dias estimados |
| Não Pagamento | XGBoost (calibrado) | — | Classificação | Probabilidade calibrada → segmentação |
| Meta Não Atingida | LightGBM | Logistic Regression | Regressão + Classificação | % projetado + flag |
| Anomalias | Isolation Forest | Z-Score + IQR | Unsupervised | Alertas com score de anomalia |

---

## Estratégia de Validação Cruzada

Para todos os modelos supervisionados:

```python
# TimeSeriesSplit — NUNCA usar KFold em dados temporais
from sklearn.model_selection import TimeSeriesSplit

tscv = TimeSeriesSplit(n_splits=5, gap=7)  # gap de 7 dias entre train/test

# Validação
for fold, (train_idx, test_idx) in enumerate(tscv.split(X)):
    X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
    y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]
    # ... treino e avaliação
```

**Regra absoluta**: Dados futuros NUNCA devem aparecer no treino. Split temporal obrigatório.

---

## Estratégia de Interpretabilidade

Para cada modelo, gerar explicações via SHAP:

```python
import shap

explainer = shap.TreeExplainer(model)
shap_values = explainer.shap_values(X_test)

# Gerar e salvar no MLflow:
# 1. Summary plot (feature importance global)
# 2. Dependence plots (top 5 features)
# 3. Sample explanations (10 exemplos de cada classe)
```

**Requisito de negócio**: Todo score publicado deve vir acompanhado das top 3 features que mais contribuíram para aquela predição individual.
