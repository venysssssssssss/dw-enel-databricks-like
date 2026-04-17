from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd

from src.data_plane.cards import build_data_cards
from src.data_plane.store import DataStore

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
                "dt_ingresso": "2025-01-02",
                "causa_raiz": "Erro de leitura - digitação",
                "texto_completo": "digitacao medidor",
                "flag_resolvido_com_refaturamento": "True",
                "has_causa_raiz_label": "True",
                "instalacao": "100",
                "status": "PROCEDENTE",
                "assunto": "REFATURAMENTO PRODUTOS",
                "grupo": "B",
            },
            {
                "ordem": "2",
                "_source_region": "CE",
                "_data_type": "erro_leitura",
                "dt_ingresso": "2026-03-26",
                "causa_raiz": "Acesso ao medidor",
                "texto_completo": "sem acesso",
                "flag_resolvido_com_refaturamento": "False",
                "has_causa_raiz_label": "True",
                "instalacao": "101",
                "status": "ABERTO",
                "assunto": "ERRO DE LEITURA",
                "grupo": "A",
            },
            {
                "ordem": "3",
                "_source_region": "SP",
                "_data_type": "base_n1_sp",
                "dt_ingresso": "2025-07-01",
                "causa_raiz": "ERRO_LEITURA",
                "texto_completo": "erro leitura",
                "flag_resolvido_com_refaturamento": "False",
                "has_causa_raiz_label": "False",
                "instalacao": "200",
                "status": "ABERTO",
                "assunto": "ERRO DE LEITURA",
                "grupo": "B",
            },
            {
                "ordem": "4",
                "_source_region": "SP",
                "_data_type": "base_n1_sp",
                "dt_ingresso": "2026-03-24",
                "causa_raiz": "ERRO_LEITURA",
                "texto_completo": "erro leitura 2",
                "flag_resolvido_com_refaturamento": "False",
                "has_causa_raiz_label": "False",
                "instalacao": "201",
                "status": "ABERTO",
                "assunto": "ERRO DE LEITURA",
                "grupo": "B",
            },
            {
                "ordem": "5",
                "_source_region": "RJ",
                "_data_type": "erro_leitura",
                "dt_ingresso": "2026-01-10",
                "causa_raiz": "fora de escopo",
                "texto_completo": "rj",
                "flag_resolvido_com_refaturamento": "True",
                "has_causa_raiz_label": "True",
                "instalacao": "300",
                "status": "PROCEDENTE",
                "assunto": "OUTRO",
                "grupo": "A",
            },
        ]
    ).to_csv(silver_path, index=False)
    return DataStore(
        silver_path=silver_path,
        topic_assignments_path=tmp_path / "missing_assignments.csv",
        topic_taxonomy_path=tmp_path / "missing_taxonomy.json",
        cache_dir=tmp_path / "cache",
    )


def test_build_data_cards_ce_scope_contains_ce_and_quality(tmp_path: Path) -> None:
    cards = build_data_cards(_store(tmp_path), regional_scope="CE")
    anchors = {card.anchor for card in cards}
    assert "regiao-ce" in anchors
    assert "regiao-sp" not in anchors
    assert "data-quality-notes" in anchors


def test_build_data_cards_sp_scope_contains_sp_and_quality(tmp_path: Path) -> None:
    cards = build_data_cards(_store(tmp_path), regional_scope="SP")
    anchors = {card.anchor for card in cards}
    assert "regiao-sp" in anchors
    assert "regiao-ce" not in anchors
    assert "data-quality-notes" in anchors


def test_build_data_cards_ce_sp_scope_contains_comparatives(tmp_path: Path) -> None:
    cards = build_data_cards(_store(tmp_path), regional_scope="CE+SP")
    anchors = {card.anchor for card in cards}
    assert {"ce-vs-sp-causas", "ce-vs-sp-refaturamento", "ce-vs-sp-mensal"} <= anchors


def test_data_quality_notes_always_present(tmp_path: Path) -> None:
    store = _store(tmp_path)
    for scope in ("CE", "SP", "CE+SP"):
        cards = build_data_cards(store, regional_scope=scope)  # type: ignore[arg-type]
        assert any(card.anchor == "data-quality-notes" for card in cards)


def test_cards_include_required_metadata_fields(tmp_path: Path) -> None:
    cards = build_data_cards(_store(tmp_path), regional_scope="CE+SP")
    assert cards
    assert all(card.region in {"CE", "SP", "CE+SP"} for card in cards)
    assert all(card.scope == "regional" for card in cards)
    assert all(card.data_source == "silver.erro_leitura_normalizado" for card in cards)
    assert all(card.dataset_version for card in cards)


def test_data_store_default_filter_excludes_non_ce_sp(tmp_path: Path) -> None:
    overview = _store(tmp_path).aggregate_records("overview")
    assert overview[0]["total_registros"] == 4


def test_regiao_sp_card_mentions_bias_note(tmp_path: Path) -> None:
    cards = build_data_cards(_store(tmp_path), regional_scope="SP")
    sp = next(card for card in cards if card.anchor == "regiao-sp")
    assert "viés" in sp.text.lower()


def test_ce_sp_scope_cards_have_expected_regions(tmp_path: Path) -> None:
    cards = build_data_cards(_store(tmp_path), regional_scope="CE+SP")
    by_anchor = {card.anchor: card.region for card in cards}
    assert by_anchor["regiao-ce"] == "CE"
    assert by_anchor["regiao-sp"] == "SP"
    assert by_anchor["ce-vs-sp-causas"] == "CE+SP"
