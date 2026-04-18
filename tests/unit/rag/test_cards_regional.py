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
        medidor_sp_path=tmp_path / "missing_medidor.csv",
        fatura_sp_path=tmp_path / "missing_fatura.xlsx",
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
    assert "sp-tipos-medidor" in anchors
    assert "sp-tipos-medidor-digitacao" in anchors
    assert "sp-causas-por-tipo-medidor" in anchors


def test_build_data_cards_ce_sp_scope_contains_comparatives(tmp_path: Path) -> None:
    cards = build_data_cards(_store(tmp_path), regional_scope="CE+SP")
    anchors = {card.anchor for card in cards}
    assert {"ce-vs-sp-causas", "ce-vs-sp-refaturamento", "ce-vs-sp-mensal"} <= anchors
    assert {
        "instalacoes-digitacao",
        "sp-tipos-medidor",
        "sp-tipos-medidor-digitacao",
        "sp-causas-por-tipo-medidor",
    } <= anchors


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


def _store_with_total(tmp_path: Path) -> DataStore:
    silver_path = tmp_path / "silver_total.csv"
    rows = []
    for i in range(10):
        rows.append(
            {
                "ordem": f"T{i}",
                "_source_region": "CE",
                "_data_type": "reclamacao_total",
                "dt_ingresso": "2025-06-01",
                "causa_raiz": "reclamacao_total_sem_causa",
                "texto_completo": "reclamacao total ce",
                "flag_resolvido_com_refaturamento": "True" if i < 2 else "False",
                "has_causa_raiz_label": "False",
                "instalacao": f"T{i}",
                "status": "PROCEDENTE",
                "assunto": "REFATURAMENTO PRODUTOS" if i < 5 else "VARIACAO CONSUMO",
                "grupo": "B" if i < 9 else "A",
            }
        )
    rows.append(
        {
            "ordem": "E1",
            "_source_region": "CE",
            "_data_type": "erro_leitura",
            "dt_ingresso": "2025-06-02",
            "causa_raiz": "Erro leitura",
            "texto_completo": "erro",
            "flag_resolvido_com_refaturamento": "True",
            "has_causa_raiz_label": "True",
            "instalacao": "E1",
            "status": "PROCEDENTE",
            "assunto": "ERRO LEITURA",
            "grupo": "B",
        }
    )
    rows.append(
        {
            "ordem": "S1",
            "_source_region": "SP",
            "_data_type": "base_n1_sp",
            "dt_ingresso": "2025-07-01",
            "causa_raiz": "ERRO_LEITURA",
            "texto_completo": "sp",
            "flag_resolvido_com_refaturamento": "False",
            "has_causa_raiz_label": "False",
            "instalacao": "S1",
            "status": "ABERTO",
            "assunto": "ERRO DE LEITURA",
            "grupo": "B",
        }
    )
    pd.DataFrame(rows).to_csv(silver_path, index=False)
    return DataStore(
        silver_path=silver_path,
        topic_assignments_path=tmp_path / "missing_assignments.csv",
        topic_taxonomy_path=tmp_path / "missing_taxonomy.json",
        medidor_sp_path=tmp_path / "missing_medidor.csv",
        fatura_sp_path=tmp_path / "missing_fatura.xlsx",
        cache_dir=tmp_path / "cache",
    )


def test_ce_total_cards_present_for_ce_scope(tmp_path: Path) -> None:
    cards = build_data_cards(_store_with_total(tmp_path), regional_scope="CE")
    anchors = {c.anchor for c in cards}
    expected = {
        "ce-reclamacoes-totais-overview",
        "ce-reclamacoes-totais-assuntos",
        "ce-reclamacoes-totais-refaturamento",
        "ce-reclamacoes-totais-evolucao",
        "ce-reclamacoes-totais-grupo",
        "ce-reclamacoes-totais-causas",
    }
    assert expected <= anchors


def test_ce_total_cards_absent_for_sp_scope(tmp_path: Path) -> None:
    cards = build_data_cards(_store_with_total(tmp_path), regional_scope="SP")
    anchors = {c.anchor for c in cards}
    assert not any(a.startswith("ce-reclamacoes-totais-") for a in anchors)


def test_ce_total_cards_all_tagged_ce_region(tmp_path: Path) -> None:
    cards = build_data_cards(_store_with_total(tmp_path), regional_scope="CE+SP")
    ce_total = [c for c in cards if c.anchor.startswith("ce-reclamacoes-totais-")]
    assert ce_total
    assert all(c.region == "CE" for c in ce_total)


def test_sp_n1_cards_present_for_sp_scope(tmp_path: Path) -> None:
    cards = build_data_cards(_store_with_total(tmp_path), regional_scope="SP")
    anchors = {c.anchor for c in cards}
    expected = {
        "sp-n1-overview",
        "sp-n1-assuntos",
        "sp-n1-causas",
        "sp-n1-mensal",
        "sp-n1-grupo",
        "sp-n1-top-instalacoes",
    }
    assert expected <= anchors


def test_sp_n1_cards_tagged_sp_region(tmp_path: Path) -> None:
    cards = build_data_cards(_store_with_total(tmp_path), regional_scope="CE+SP")
    sp_cards = [c for c in cards if c.anchor.startswith("sp-n1-")]
    assert sp_cards
    assert all(c.region == "SP" for c in sp_cards)


def test_ce_top_instalacoes_card_present(tmp_path: Path) -> None:
    cards = build_data_cards(_store_with_total(tmp_path), regional_scope="CE")
    anchors = {c.anchor for c in cards}
    assert "ce-top-instalacoes" in anchors
    assert "ce-reclamacoes-totais-mensal-assuntos" in anchors
    assert "ce-reclamacoes-totais-mensal-causas" in anchors


def test_ce_total_overview_card_cites_reclamacao_total_universe(tmp_path: Path) -> None:
    cards = build_data_cards(_store_with_total(tmp_path), regional_scope="CE")
    overview = next(c for c in cards if c.anchor == "ce-reclamacoes-totais-overview")
    # O overview de reclamações totais deve cobrir 10 linhas reclamacao_total,
    # não o subset erro_leitura (1 linha).
    assert "10" in overview.text


def test_ce_sp_scope_cards_have_expected_regions(tmp_path: Path) -> None:
    cards = build_data_cards(_store(tmp_path), regional_scope="CE+SP")
    by_anchor = {card.anchor: card.region for card in cards}
    assert by_anchor["regiao-ce"] == "CE"
    assert by_anchor["regiao-sp"] == "SP"
    assert by_anchor["ce-vs-sp-causas"] == "CE+SP"
