from __future__ import annotations

import pandas as pd

from src.viz.reclamacoes_ce_dashboard_data import (
    MACRO_TEMA_LABELS,
    MACRO_TEMA_ORDER,
    assunto_pareto,
    causa_raiz_drill,
    classify_macro_tema,
    compute_kpis,
    cruzamento_com_erro_leitura,
    executive_summary,
    heatmap_tema_x_mes,
    macro_tema_distribution,
    monthly_trend_by_tema,
    prepare_reclamacoes_ce_frame,
    radar_tema_por_grupo,
    reincidence_matrix,
    top_instalacoes_reincidentes,
)


def _silver_frame() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "_source_region": "CE",
                "_data_type": "reclamacao_total",
                "grupo": "GB",
                "ordem": "1",
                "assunto": "REFATURAMENTO PRODUTOS",
                "instalacao": "100",
                "dt_ingresso": "2025-05-10",
                "causa_raiz": "ERRO DE LEITURA - DIGITAÇÃO",
            },
            {
                "_source_region": "CE",
                "_data_type": "reclamacao_total",
                "grupo": "GB",
                "ordem": "2",
                "assunto": "REFAT MULTA A REVELIA",
                "instalacao": "100",
                "dt_ingresso": "2025-06-02",
                "causa_raiz": "",
            },
            {
                "_source_region": "CE",
                "_data_type": "reclamacao_total",
                "grupo": "GA",
                "ordem": "3",
                "assunto": "REC DA FATURA COM GD",
                "instalacao": "200",
                "dt_ingresso": "2025-07-15",
                "causa_raiz": "COMPENSAÇÃO DE ENERGIA INJETADA INCORRETA",
            },
            {
                "_source_region": "CE",
                "_data_type": "reclamacao_total",
                "grupo": "GB",
                "ordem": "4",
                "assunto": "CONTA NÃO ENTREGUE",
                "instalacao": "300",
                "dt_ingresso": "2025-07-20",
                "causa_raiz": "",
            },
            {
                "_source_region": "CE",
                "_data_type": "erro_leitura",
                "grupo": "GB",
                "ordem": "5",
                "assunto": "ERRO DE LEITURA",
                "instalacao": "100",
                "dt_ingresso": "2025-04-01",
                "causa_raiz": "ERRO DE LEITURA - DIGITAÇÃO",
            },
            {
                "_source_region": "SP",
                "_data_type": "base_n1_sp",
                "grupo": "",
                "ordem": "6",
                "assunto": "x",
                "instalacao": "999",
                "dt_ingresso": "2025-08-01",
                "causa_raiz": "",
            },
        ]
    )


def test_classify_macro_tema_covers_known_patterns() -> None:
    assert classify_macro_tema("REFATURAMENTO PRODUTOS") == "refaturamento"
    assert classify_macro_tema("REC DA FATURA COM GD") == "geracao_distribuida"
    assert classify_macro_tema("REFAT MULTA A REVELIA") == "religacao_multas"
    assert classify_macro_tema("CONTA NÃO ENTREGUE") == "entrega_fatura"
    assert classify_macro_tema("VARIAÇÃO DE CONSUMO") == "variacao_consumo"
    assert classify_macro_tema("REC FATURAMENTO POR MEDIA") == "media_estimativa"
    assert classify_macro_tema("OUV FATURAMENTO AUD") == "ouvidoria_juridico"
    assert classify_macro_tema("") == "outros"
    assert classify_macro_tema(None) == "outros"


def test_prepare_frame_filters_ce_reclamacao_total_only() -> None:
    frame = prepare_reclamacoes_ce_frame(_silver_frame())
    assert set(frame["ordem"]) == {"1", "2", "3", "4"}
    assert (frame["_source_region"] == "CE").all()
    assert (frame["_data_type"] == "reclamacao_total").all()
    assert "macro_tema" in frame.columns
    assert "instalacao_hash" in frame.columns
    assert frame.loc[frame["ordem"] == "1", "macro_tema"].item() == "refaturamento"
    assert frame.loc[frame["ordem"] == "3", "macro_tema"].item() == "geracao_distribuida"


def test_compute_kpis_and_executive_summary() -> None:
    frame = prepare_reclamacoes_ce_frame(_silver_frame())
    kpis = compute_kpis(frame)
    assert kpis.total_reclamacoes == 4
    assert kpis.unique_instalacoes == 3
    assert kpis.instalacoes_reincidentes == 1  # instalacao 100 aparece 2x
    assert 0 < kpis.share_grupo_b < 1
    assert kpis.assuntos_distintos == 4
    summary = executive_summary(frame)
    assert not summary.empty
    assert set(summary.columns) == {"Métrica", "Valor"}


def test_macro_tema_distribution_and_pareto() -> None:
    frame = prepare_reclamacoes_ce_frame(_silver_frame())
    dist = macro_tema_distribution(frame)
    assert dist["qtd"].sum() == 4
    assert abs(dist["percentual"].sum() - 100.0) < 0.001
    pareto = assunto_pareto(frame, top_n=10)
    assert pareto["qtd"].sum() == 4
    assert pareto["acumulado_pct"].iloc[-1] <= 100.0001


def test_causa_raiz_drill_filters_by_tema() -> None:
    frame = prepare_reclamacoes_ce_frame(_silver_frame())
    drill_ref = causa_raiz_drill(frame, macro_tema="refaturamento")
    assert not drill_ref.empty
    assert "ERRO DE LEITURA - DIGITAÇÃO" in drill_ref["causa_raiz"].values
    drill_gd = causa_raiz_drill(frame, macro_tema="geracao_distribuida")
    assert drill_gd["causa_raiz"].iloc[0] == "COMPENSAÇÃO DE ENERGIA INJETADA INCORRETA"


def test_monthly_trend_has_rolling_mean() -> None:
    frame = prepare_reclamacoes_ce_frame(_silver_frame())
    trend = monthly_trend_by_tema(frame)
    assert "media_movel_3m" in trend.columns
    assert "mom" in trend.columns
    assert trend["media_movel_3m"].notna().any()


def test_heatmap_tema_x_mes_returns_ordered_index() -> None:
    frame = prepare_reclamacoes_ce_frame(_silver_frame())
    heat = heatmap_tema_x_mes(frame)
    assert not heat.empty
    order_labels = [MACRO_TEMA_LABELS[t] for t in MACRO_TEMA_ORDER]
    assert list(heat.index) == [lbl for lbl in order_labels if lbl in heat.index]


def test_top_instalacoes_reincidentes_ordering() -> None:
    frame = prepare_reclamacoes_ce_frame(_silver_frame())
    top = top_instalacoes_reincidentes(frame, top_n=5)
    assert top["qtd_reclamacoes"].iloc[0] == 2
    assert top["qtd_reclamacoes"].is_monotonic_decreasing


def test_radar_has_all_themes_for_each_grupo() -> None:
    frame = prepare_reclamacoes_ce_frame(_silver_frame())
    radar = radar_tema_por_grupo(frame)
    grupos = radar["grupo"].unique().tolist()
    for grupo in grupos:
        assert set(radar.loc[radar["grupo"] == grupo, "macro_tema_label"]) == set(
            MACRO_TEMA_LABELS.values()
        )


def test_reincidence_matrix_buckets() -> None:
    frame = prepare_reclamacoes_ce_frame(_silver_frame())
    matrix = reincidence_matrix(frame)
    assert list(matrix["bucket"]) == ["1", "2", "3-4", "5-9", "10+"]
    assert matrix["instalacoes"].sum() == 3  # 3 instalacoes distintas


def test_cruzamento_com_erro_leitura_finds_intersection() -> None:
    silver = _silver_frame()
    reclamacoes = prepare_reclamacoes_ce_frame(silver)
    # Simula erro_leitura_frame com instalacao_hash compatível (mesmo hash sha256[:12])
    from hashlib import sha256

    erro_frame = pd.DataFrame(
        [
            {
                "_source_region": "CE",
                "instalacao_hash": sha256(b"100").hexdigest()[:12],
            }
        ]
    )
    cross = cruzamento_com_erro_leitura(reclamacoes, erro_frame)
    assert not cross.empty
    # Instalacao 100 aparece em 2 ordens: uma em 'refaturamento' e outra em 'religacao_multas'.
    assert int(cross["qtd_com_erro_leitura"].sum()) == 2


def test_empty_frame_handling_is_safe() -> None:
    empty = prepare_reclamacoes_ce_frame(
        pd.DataFrame(columns=["_source_region", "_data_type", "assunto", "ordem", "dt_ingresso"])
    )
    assert empty.empty
    assert compute_kpis(empty).total_reclamacoes == 0
    assert macro_tema_distribution(empty).empty
    assert assunto_pareto(empty).empty
    assert monthly_trend_by_tema(empty).empty
    assert heatmap_tema_x_mes(empty).empty
    assert top_instalacoes_reincidentes(empty).empty
    assert radar_tema_por_grupo(empty).empty
    assert reincidence_matrix(empty).empty
