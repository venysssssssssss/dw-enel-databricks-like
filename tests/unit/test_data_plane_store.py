from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd

from src.data_plane import DataStore

if TYPE_CHECKING:
    from pathlib import Path


def _write_silver(path: Path) -> None:
    pd.DataFrame(
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
                "grupo": "B",
            },
            {
                "ordem": "2",
                "_source_region": "SP",
                "_data_type": "base_n1_sp",
                "dt_ingresso": "2026-02-01",
                "causa_raiz": "",
                "texto_completo": "portao fechado sem acesso ao medidor",
                "flag_resolvido_com_refaturamento": "False",
                "has_causa_raiz_label": "False",
                "instalacao": "100",
                "status": "ABERTO",
                "assunto": "ACESSO",
                "grupo": "A",
            },
            {
                "ordem": "3",
                "_source_region": "CE",
                "_data_type": "reclamacao_total",
                "dt_ingresso": "2026-03-01",
                "causa_raiz": "",
                "texto_completo": "reclamacao total fora do treinamento",
                "flag_resolvido_com_refaturamento": "False",
                "has_causa_raiz_label": "False",
                "instalacao": "200",
                "status": "ABERTO",
                "assunto": "TOTAL",
                "grupo": "B",
            },
        ]
    ).to_csv(path, index=False)


def test_data_store_aggregates_from_prepared_silver(tmp_path: Path) -> None:
    silver_path = tmp_path / "silver.csv"
    _write_silver(silver_path)
    store = DataStore(
        silver_path=silver_path,
        topic_assignments_path=tmp_path / "missing_assignments.csv",
        topic_taxonomy_path=tmp_path / "missing_taxonomy.json",
        medidor_sp_path=tmp_path / "missing_medidor.csv",
        fatura_sp_path=tmp_path / "missing_fatura.xlsx",
        cache_dir=tmp_path / "cache",
    )

    overview = store.aggregate_records("overview")
    by_region = store.aggregate_records("by_region", {"regiao": ["CE"]})

    assert overview[0]["total_registros"] == 2
    assert overview[0]["instalacoes_reincidentes"] == 1
    assert by_region == [
        {
            "regiao": "CE",
            "qtd_ordens": 1,
            "taxa_refaturamento": 1.0,
            "ordens_refaturadas": 1,
            "causas_rotuladas": 1,
        }
    ]


def test_data_store_cards_share_dataset_version(tmp_path: Path) -> None:
    silver_path = tmp_path / "silver.csv"
    _write_silver(silver_path)
    store = DataStore(
        silver_path=silver_path,
        topic_assignments_path=tmp_path / "missing_assignments.csv",
        topic_taxonomy_path=tmp_path / "missing_taxonomy.json",
        medidor_sp_path=tmp_path / "missing_medidor.csv",
        fatura_sp_path=tmp_path / "missing_fatura.xlsx",
        cache_dir=tmp_path / "cache",
    )

    version = store.version()
    cards = store.cards()

    assert cards
    assert {card.dataset_version for card in cards} == {version.hash}
    assert all(card.doc_type == "data" for card in cards)
