from __future__ import annotations

from datetime import date, timedelta

import pandas as pd

from src.ml.feature_store import FeatureStore
from src.ml.features import AtrasoFeatureBuilder, InadimplenciaFeatureBuilder
from src.ml.models import AtrasoModelTrainer, MetasModelTrainer
from src.ml.monitoring import DriftDetector
from src.ml.scoring import AtrasoScorer


def _build_notas_frame() -> pd.DataFrame:
    rows = []
    for index in range(1, 41):
        created_at = date(2026, 1, 1) + timedelta(days=index * 2)
        planned_at = created_at + timedelta(days=2)
        delayed = index % 4 == 0
        executed_at = planned_at + timedelta(days=3 if delayed else 0)
        rows.append(
            {
                "cod_nota": index,
                "cod_uc": 100 + (index % 5),
                "cod_base": 10 + (index % 3),
                "cod_colaborador": 200 + (index % 4),
                "data_criacao": created_at.isoformat(),
                "data_prevista": planned_at.isoformat(),
                "data_execucao": executed_at.isoformat(),
                "status": "DEVOLVIDA" if delayed else "EXECUTADA",
                "historico_incidentes_12m": index % 3,
                "flag_impacto_faturamento": "true" if index % 2 == 0 else "false",
                "area_classificada_risco": "true" if index % 5 == 0 else "false",
                "flag_risco_manual": "true" if index % 7 == 0 else "false",
            }
        )
    rows.append(
        {
            "cod_nota": 999,
            "cod_uc": 105,
            "cod_base": 12,
            "cod_colaborador": 203,
            "data_criacao": "2026-12-31",
            "data_prevista": "2027-01-02",
            "data_execucao": "2027-01-03",
            "status": "EXECUTADA",
            "historico_incidentes_12m": 0,
            "flag_impacto_faturamento": "false",
            "area_classificada_risco": "false",
            "flag_risco_manual": "false",
        }
    )
    return pd.DataFrame(rows)


def _build_pagamentos_frame() -> pd.DataFrame:
    rows = []
    for index in range(1, 13):
        due_date = date(2026, index, 10)
        late = index in {2, 3, 4, 7, 8, 12}
        rows.append(
            {
                "cod_fatura": index,
                "cod_uc": 501 if index <= 6 else 502,
                "valor_fatura": 100.0 + index,
                "valor_pago": 100.0 + index if not late else 0.0,
                "data_vencimento": due_date.isoformat(),
                "data_pagamento": None if late else (due_date + timedelta(days=1)).isoformat(),
            }
        )
    return pd.DataFrame(rows)


def _build_ucs_frame() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"cod_uc": 501, "cod_base": 10, "classe_consumo": "RESIDENCIAL"},
            {"cod_uc": 502, "cod_base": 11, "classe_consumo": "COMERCIAL"},
        ]
    )


def _build_metas_feature_snapshot(observation_date: date) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "cod_base": 10,
                "valor_meta": 100.0,
                "valor_realizado": 70.0 if observation_date.month % 2 == 0 else 95.0,
                "pct_atingimento": 70.0 if observation_date.month % 2 == 0 else 95.0,
                "lag_1_pct": 80.0,
                "lag_3_media_pct": 85.0,
                "gap_meta": 30.0 if observation_date.month % 2 == 0 else 5.0,
                "tendencia_mensal": -5.0 if observation_date.month % 2 == 0 else 4.0,
                "target_pct_atingimento": 70.0 if observation_date.month % 2 == 0 else 95.0,
                "target_flag_risco": 1 if observation_date.month % 2 == 0 else 0,
                "_observation_date": observation_date.isoformat(),
            },
            {
                "cod_base": 11,
                "valor_meta": 100.0,
                "valor_realizado": 92.0,
                "pct_atingimento": 92.0,
                "lag_1_pct": 90.0,
                "lag_3_media_pct": 91.0,
                "gap_meta": 8.0,
                "tendencia_mensal": 1.0,
                "target_pct_atingimento": 92.0,
                "target_flag_risco": 0,
                "_observation_date": observation_date.isoformat(),
            },
        ]
    )


def test_atraso_feature_builder_respects_observation_date() -> None:
    frame = AtrasoFeatureBuilder(date(2026, 3, 1)).build(_build_notas_frame())
    assert 999 not in frame["cod_nota"].tolist()
    assert frame["target_flag_atraso"].sum() > 0
    assert frame["_observation_date"].eq("2026-03-01").all()


def test_inadimplencia_feature_builder_calculates_consecutive_months() -> None:
    frame = InadimplenciaFeatureBuilder(date(2026, 12, 31)).build(
        _build_pagamentos_frame(),
        _build_ucs_frame(),
    )
    uc_501 = frame.loc[frame["cod_uc"] == 501]
    assert int(uc_501["meses_consecutivos_inadimplente"].max()) >= 3
    assert "taxa_inadimplencia_base" in frame.columns


def test_feature_store_training_and_batch_scoring_roundtrip(tmp_path) -> None:
    store = FeatureStore(tmp_path / "feature_store")
    notas = _build_notas_frame()
    for observation_date in [date(2026, 2, 1), date(2026, 3, 1), date(2026, 4, 1)]:
        features = AtrasoFeatureBuilder(observation_date).build(notas)
        store.save(
            "atraso_entrega",
            observation_date,
            features,
            entity_key="cod_nota",
            target_columns=["target_flag_atraso", "target_dias_atraso"],
        )

    trainer = AtrasoModelTrainer(store)
    result = trainer.train(date(2026, 3, 1))
    assert result.train_rows > 0
    assert result.test_rows > 0

    scorer = AtrasoScorer("atraso_entrega", store, registry=trainer.registry, scores_root=tmp_path / "scores")
    scoring_result = scorer.score(date(2026, 4, 1))
    assert scoring_result.rows_scored > 0
    scored = pd.read_csv(scoring_result.output_path)
    assert scored["score"].between(0.0, 1.0).all()


def test_drift_detector_flags_distribution_shift(tmp_path) -> None:
    store = FeatureStore(tmp_path / "feature_store")
    reference = pd.DataFrame(
        {
            "entidade_id": ["a", "b", "c", "d"],
            "total_notas": [10.0, 11.0, 9.0, 10.5],
            "_observation_date": ["2026-02-01"] * 4,
        }
    )
    current = pd.DataFrame(
        {
            "entidade_id": ["a", "b", "c", "d"],
            "total_notas": [30.0, 28.0, 35.0, 31.0],
            "_observation_date": ["2026-03-01"] * 4,
        }
    )
    store.save("anomalias", date(2026, 2, 1), reference, entity_key="entidade_id")
    store.save("anomalias", date(2026, 3, 1), current, entity_key="entidade_id")

    results = DriftDetector("anomalias", store).check_feature_drift(date(2026, 2, 1), date(2026, 3, 1))
    assert any(result.status in {"WARNING", "CRITICAL"} for result in results)


def test_metas_model_explain_prediction(tmp_path) -> None:
    store = FeatureStore(tmp_path / "feature_store")
    for observation_date in [date(2026, 1, 1), date(2026, 2, 1), date(2026, 3, 1)]:
        store.save("metas", observation_date, _build_metas_feature_snapshot(observation_date), entity_key="cod_base")

    trainer = MetasModelTrainer(store)
    training_result = trainer.train(date(2026, 3, 1))
    bundle = trainer.registry.load_bundle("metas", training_result.version)
    explanation = trainer.explain_prediction(bundle, _build_metas_feature_snapshot(date(2026, 3, 1)).head(1))
    assert explanation["status"] in {"EM_RISCO", "NO_CAMINHO"}
    assert len(explanation["explicacao"]) == 3
