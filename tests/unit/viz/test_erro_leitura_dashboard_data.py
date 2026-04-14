from __future__ import annotations

import pandas as pd

from src.viz.erro_leitura_dashboard_data import (
    compute_kpis,
    monthly_volume,
    prepare_dashboard_frame,
    refaturamento_by_cause,
    region_cause_matrix,
    root_cause_distribution,
    safe_topic_taxonomy_for_display,
    topic_distribution,
)


def _silver_frame() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "ordem": "1",
                "_source_region": "CE",
                "_data_type": "erro_leitura",
                "dt_ingresso": "2026-01-10",
                "causa_raiz": "Erro de leitura - digitação",
                "texto_completo": "leitura errada por digitacao",
                "flag_resolvido_com_refaturamento": "True",
                "has_causa_raiz_label": "True",
                "instalacao": "100",
                "status": "PROCEDENTE",
                "assunto": "ERRO",
            },
            {
                "ordem": "2",
                "_source_region": "CE",
                "_data_type": "reclamacao_total",
                "dt_ingresso": "2026-01-11",
                "causa_raiz": "",
                "texto_completo": "reclamacao generica",
                "flag_resolvido_com_refaturamento": "False",
                "has_causa_raiz_label": "False",
                "instalacao": "200",
                "status": "ABERTO",
                "assunto": "TOTAL",
            },
            {
                "ordem": "3",
                "_source_region": "SP",
                "_data_type": "base_n1_sp",
                "dt_ingresso": "2026-02-01",
                "causa_raiz": "",
                "texto_completo": "portao fechado sem acesso ao medidor",
                "flag_resolvido_com_refaturamento": "False",
                "has_causa_raiz_label": "False",
                "instalacao": "100",
                "status": "ABERTO",
                "assunto": "ERRO",
            },
        ]
    )


def _topic_assignments() -> pd.DataFrame:
    return pd.DataFrame({"ordem": ["1", "3"], "topic_id": [10, 20]})


def _topic_taxonomy() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "topic_id": 10,
                "topic_name": "ajuste_digitacao",
                "topic_size": 1,
                "keywords": ["ajuste", "digitacao"],
                "examples": ["celular: 11999998888 pessoa@example.com"],
            },
            {
                "topic_id": 20,
                "topic_name": "acesso_medidor",
                "topic_size": 1,
                "keywords": ["acesso", "medidor"],
                "examples": ["portao fechado"],
            },
        ]
    )


def test_prepare_dashboard_frame_filters_total_and_sanitizes_columns() -> None:
    frame = prepare_dashboard_frame(
        _silver_frame(),
        topic_assignments=_topic_assignments(),
        topic_taxonomy=_topic_taxonomy(),
    )
    assert frame["ordem"].tolist() == ["1", "3"]
    assert "texto_completo" not in frame.columns
    assert "observacao_ordem" not in frame.columns
    assert frame.loc[frame["ordem"].eq("1"), "causa_canonica"].item() == "digitacao"
    assert frame.loc[frame["ordem"].eq("3"), "causa_canonica"].item() == "acesso_negado"
    assert frame["instalacao_hash"].nunique() == 1


def test_prepare_dashboard_frame_can_include_total() -> None:
    frame = prepare_dashboard_frame(_silver_frame(), include_total=True)
    assert len(frame) == 3


def test_dashboard_aggregations_return_visual_shapes() -> None:
    frame = prepare_dashboard_frame(
        _silver_frame(),
        topic_assignments=_topic_assignments(),
        topic_taxonomy=_topic_taxonomy(),
    )
    kpis = compute_kpis(frame)
    assert kpis.total_registros == 2
    assert kpis.instalacoes_reincidentes == 1
    assert not monthly_volume(frame).empty
    assert not root_cause_distribution(frame).empty
    assert "CE" in region_cause_matrix(frame).columns
    assert not topic_distribution(frame).empty
    assert not refaturamento_by_cause(frame).empty


def test_safe_topic_taxonomy_masks_examples() -> None:
    taxonomy = safe_topic_taxonomy_for_display(_topic_taxonomy())
    examples = taxonomy.loc[taxonomy["topic_name"].eq("ajuste_digitacao"), "examples"].item()
    joined = " ".join(examples)
    assert "11999998888" not in joined
    assert "pessoa@example.com" not in joined
    assert "[TELEFONE]" in joined
    assert "[EMAIL]" in joined
