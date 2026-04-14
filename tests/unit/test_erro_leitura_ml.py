from __future__ import annotations

import pandas as pd

from src.ml.features.text_embeddings import TextEmbeddingBuilder
from src.ml.models.erro_leitura_anomaly import ErroLeituraAnomalyDetector
from src.ml.models.erro_leitura_classifier import ErroLeituraClassifierTrainer, KeywordErroLeituraClassifier, canonical_label
from src.ml.models.erro_leitura_topic_model import (
    ErroLeituraTopicModelTrainer,
    _taxonomy_example,
    _topic_training_text,
    mask_sensitive_text,
)
from scripts.train_erro_leitura import _filter_training_frame


def _training_frame() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "ordem": "1",
                "texto_completo": "cliente informa leitura estimada ha meses",
                "causa_raiz": "leitura_estimada",
                "dt_ingresso": "2026-01-01",
                "_source_region": "CE",
            },
            {
                "ordem": "2",
                "texto_completo": "medidor quebrado com visor danificado",
                "causa_raiz": "medidor_danificado",
                "dt_ingresso": "2026-01-02",
                "_source_region": "CE",
            },
            {
                "ordem": "3",
                "texto_completo": "portao fechado impede acesso ao medidor",
                "causa_raiz": "impedimento_acesso",
                "dt_ingresso": "2026-01-03",
                "_source_region": "SP",
            },
            {
                "ordem": "4",
                "texto_completo": "endereco divergente na ordem",
                "causa_raiz": "endereco_tipologia",
                "dt_ingresso": "2026-01-04",
                "_source_region": "SP",
            },
            {
                "ordem": "5",
                "texto_completo": "leitura errada por digitacao",
                "causa_raiz": "digitacao",
                "dt_ingresso": "2026-01-05",
                "_source_region": "CE",
            },
            {
                "ordem": "6",
                "texto_completo": "fatura corrigida apos refaturamento",
                "causa_raiz": "refaturamento_corretivo",
                "dt_ingresso": "2026-01-06",
                "_source_region": "CE",
            },
        ]
    )


def test_text_embedding_builder_returns_stable_columns() -> None:
    result = TextEmbeddingBuilder(dimensions=4).build(_training_frame())
    assert result.backend == "tfidf-svd"
    assert "ordem" in result.frame.columns
    assert any(column.startswith("embedding_") for column in result.frame.columns)


def test_topic_model_discovers_taxonomy() -> None:
    result = ErroLeituraTopicModelTrainer(min_topic_size=2, max_topics=3).train(_training_frame())
    assert not result.assignments.empty
    assert not result.taxonomy.empty
    assert result.backend == "sklearn-kmeans"
    assert "de" not in result.taxonomy.iloc[0]["keywords"]


def test_topic_examples_mask_sensitive_values() -> None:
    masked = mask_sensitive_text(
        "gmtuk maria silva (br123456) celular: 11999998888 protocolo 123456 "
        "cep 12345-678 email pessoa@example.com"
    )
    assert "11999998888" not in masked
    assert "123456" not in masked
    assert "12345-678" not in masked
    assert "pessoa@example.com" not in masked
    assert "maria silva" not in masked


def test_taxonomy_examples_are_bounded() -> None:
    example = _taxonomy_example("x" * 1000)
    assert len(example) < 500
    assert example.endswith("...")


def test_topic_training_text_removes_internal_user_tokens() -> None:
    text = _topic_training_text("gmtuk elaine cristina feitosa reclama erro br123456 pessoa@example.com")
    assert "elaine" not in text
    assert "cristina" not in text
    assert "feitosa" not in text
    assert "br123456" not in text
    assert "pessoa@example.com" not in text


def test_keyword_classifier_classifies_access_issue() -> None:
    result = KeywordErroLeituraClassifier().classify(
        "portao fechado sem acesso ao medidor, cliente nao da acesso"
    )
    assert result["classe"] == "impedimento_acesso"
    assert len(result["top3"]) == 3


def test_canonical_label_consolidates_source_variants() -> None:
    assert canonical_label("Erro de leitura - digitação") == "digitacao"
    assert canonical_label("Faturamento por média - cliente") == "leitura_estimada_media"
    assert canonical_label("Erro de tipologia outra área") == "endereco_tipologia"
    assert canonical_label("outros") is None


def test_classifier_training_returns_macro_f1() -> None:
    result = ErroLeituraClassifierTrainer(TextEmbeddingBuilder(dimensions=4)).train(_training_frame())
    assert result.backend == "logistic-regression-calibrated"
    assert result.macro_f1 >= 0.0
    assert "impedimento_acesso" in result.classes


def test_anomaly_detector_outputs_hotspots() -> None:
    frame = pd.DataFrame(
        [
            {"dt_ingresso": "2026-01-01", "_source_region": "CE", "classe_erro": "leitura_estimada"},
            {"dt_ingresso": "2026-01-02", "_source_region": "CE", "classe_erro": "leitura_estimada"},
            {"dt_ingresso": "2026-01-03", "_source_region": "CE", "classe_erro": "leitura_estimada"},
            {"dt_ingresso": "2026-01-03", "_source_region": "CE", "classe_erro": "leitura_estimada"},
            {"dt_ingresso": "2026-01-03", "_source_region": "CE", "classe_erro": "leitura_estimada"},
        ]
    )
    result = ErroLeituraAnomalyDetector().detect(frame)
    assert {"qtd_erros", "zscore", "anomaly_score", "is_anomaly"}.issubset(result.columns)


def test_training_filter_excludes_total_by_default() -> None:
    frame = pd.DataFrame(
        [
            {"ordem": "1", "_data_type": "reclamacao_total"},
            {"ordem": "2", "_data_type": "erro_leitura"},
            {"ordem": "3", "_data_type": "base_n1_sp"},
        ]
    )
    filtered = _filter_training_frame(frame, include_total=False)
    assert filtered["ordem"].tolist() == ["2", "3"]
    assert len(_filter_training_frame(frame, include_total=True)) == 3
