from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd

from src.data_plane import DataStore

if TYPE_CHECKING:
    from pathlib import Path


def _store(tmp_path: Path) -> DataStore:
    silver_path = tmp_path / "silver.csv"
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
                "instalacao": "200",
                "status": "ABERTO",
                "assunto": "ACESSO",
                "grupo": "A",
            },
        ]
    ).to_csv(silver_path, index=False)
    return DataStore(
        silver_path=silver_path,
        topic_assignments_path=tmp_path / "missing_assignments.csv",
        topic_taxonomy_path=tmp_path / "missing_taxonomy.json",
        medidor_sp_path=tmp_path / "missing_medidor.csv",
        fatura_sp_path=tmp_path / "missing_fatura.xlsx",
        cache_dir=tmp_path / "cache",
    )


def test_bi_aggregations_and_rag_cards_share_numbers_and_version(tmp_path: Path) -> None:
    store = _store(tmp_path)
    version = store.version()
    overview = store.aggregate_records("overview")[0]
    by_region = store.aggregate_records("by_region")
    cards = store.cards()
    card_text = "\n".join(card.text for card in cards)

    assert overview["total_registros"] == 2
    assert {row["regiao"]: row["qtd_ordens"] for row in by_region} == {"CE": 1, "SP": 1}
    assert {card.dataset_version for card in cards} == {version.hash}
    assert "2 ordens" in card_text
    assert "Reclamações na região CE" in card_text
    assert "Reclamações na região SP" in card_text
