from __future__ import annotations

import pandas as pd

from scripts.relabel_erro_leitura import coverage_report, relabel_frame
from src.ml.models.erro_leitura_classifier import (
    KeywordErroLeituraClassifier,
    TaxonomyEntry,
    _is_resolucao_pura,
    _is_texto_incompleto,
    taxonomy_metadata,
)
from src.viz.erro_leitura_dashboard_data import (
    _filter_sp_severidade,
    classifier_coverage,
    classifier_indefinido_tokens,
    prepare_dashboard_frame,
)


def test_taxonomy_v3_exposes_18_classes() -> None:
    meta = taxonomy_metadata()
    expected = {
        "procedimento_administrativo",
        "ajuste_numerico_sem_causa",
        "texto_incompleto",
        "solicitacao_canal_atendimento",
    }
    assert len(meta) == 18
    assert expected.issubset(set(meta["classe"]))
    assert set(meta.loc[meta["classe"].isin(expected), "severidade"]) == {"low"}


def test_keyword_classifier_v3_classifies_new_semantic_buckets() -> None:
    classifier = KeywordErroLeituraClassifier()

    admin = classifier.classify("procedente - corrigido conforme solicitado")
    numeric = classifier.classify("corrigido consumo da ref 202506 para 24 kwh")
    incomplete = classifier.classify("refat")
    channel = classifier.classify("contato via email para retorno do atendimento")

    assert admin["classe"] == "procedimento_administrativo"
    assert admin["confidence"] == "high"
    assert numeric["classe"] == "ajuste_numerico_sem_causa"
    assert incomplete["classe"] == "texto_incompleto"
    assert incomplete["confidence"] == "high"
    assert channel["classe"] == "solicitacao_canal_atendimento"


def test_keyword_classifier_keeps_existing_strong_causes() -> None:
    result = KeywordErroLeituraClassifier().classify("medidor queimado com visor danificado")

    assert result["classe"] == "medidor_danificado"
    assert result["confidence"] == "high"


def test_keyword_classifier_exposes_low_confidence_bucket() -> None:
    classifier = KeywordErroLeituraClassifier(
        taxonomy={
            "classe_a": TaxonomyEntry(
                description="a",
                category="teste",
                severity="low",
                keywords=(("alfa", 0.8),),
            ),
            "classe_b": TaxonomyEntry(
                description="b",
                category="teste",
                severity="low",
                keywords=(("beta", 0.1),),
            ),
        }
    )

    result = classifier.classify("alfa")

    assert result["classe"] == "classe_a"
    assert result["confidence"] == "low"


def test_resolution_pure_regex_is_conservative() -> None:
    positives = [
        "procedente conforme solicitado",
        "ajuste realizado",
        "ajuste concluido",
        "fatura atualizada para pagamento",
        "refat ok",
    ]
    negatives = [
        "procedente conforme solicitado por medidor queimado",
        "ajuste realizado por digitacao incorreta",
        "fatura atualizada para pgto por consumo elevado",
        "leiturista digitou errado",
        "impedimento de acesso confirmado",
    ]

    assert all(_is_resolucao_pura(text) for text in positives)
    assert not any(_is_resolucao_pura(text) for text in negatives)


def test_incomplete_text_regex_flags_short_truncated_notes() -> None:
    assert _is_texto_incompleto("refat")
    assert _is_texto_incompleto("conf ajuste inst")
    assert not _is_texto_incompleto("refaturamento confirmado conforme solicitado")


def test_prepare_dashboard_frame_applies_topic_mapping_only_for_indefinido() -> None:
    silver = pd.DataFrame(
        [
            {
                "ordem": "1",
                "_source_region": "SP",
                "_data_type": "base_n1_sp",
                "dt_ingresso": "2026-01-01",
                "causa_raiz": "",
                "texto_completo": "texto sem sinal operacional claro",
                "flag_resolvido_com_refaturamento": "False",
                "has_causa_raiz_label": "False",
                "instalacao": "100",
                "status": "ABERTO",
                "assunto": "ERRO",
            },
            {
                "ordem": "2",
                "_source_region": "SP",
                "_data_type": "base_n1_sp",
                "dt_ingresso": "2026-01-01",
                "causa_raiz": "",
                "texto_completo": "medidor queimado com visor danificado",
                "flag_resolvido_com_refaturamento": "False",
                "has_causa_raiz_label": "False",
                "instalacao": "200",
                "status": "ABERTO",
                "assunto": "ERRO",
            },
        ]
    )
    assignments = pd.DataFrame({"ordem": ["1", "2"], "topic_id": [3, 3]})
    mapping = pd.DataFrame(
        {
            "topic_id": ["3"],
            "canonical_target": ["procedimento_administrativo"],
            "confidence": ["low"],
        }
    )

    out = prepare_dashboard_frame(
        silver,
        topic_assignments=assignments,
        topic_to_canonical=mapping,
    )

    by_order = out.set_index("ordem")
    assert by_order.loc["1", "causa_canonica"] == "procedimento_administrativo"
    assert by_order.loc["1", "causa_canonica_confidence"] == "low"
    assert by_order.loc["2", "causa_canonica"] == "medidor_danificado"
    assert by_order.loc["2", "causa_canonica_confidence"] == "high"


def test_filter_sp_severidade_defaults_to_high_confidence() -> None:
    frame = pd.DataFrame(
        [
            _severity_row("a", confidence="high"),
            _severity_row("b", confidence="low"),
            _severity_row("c", confidence="indefinido"),
        ]
    )

    strict = _filter_sp_severidade(frame, "high")
    permissive = _filter_sp_severidade(frame, "high", min_confidence="low")

    assert strict["ordem"].tolist() == ["a"]
    assert permissive["ordem"].tolist() == ["a", "b"]


def test_classifier_coverage_and_tokens_views() -> None:
    frame = pd.DataFrame(
        [
            _coverage_row("a", "SP", "indefinido", "indefinido", "mail, anexo", "ERRO"),
            _coverage_row("b", "SP", "digitacao", "high", "digitacao", "ERRO"),
            _coverage_row("c", "CE", "procedimento_administrativo", "low", "ajuste", "AJUSTE"),
        ]
    )

    coverage = classifier_coverage(frame)
    tokens = classifier_indefinido_tokens(frame)

    sp = coverage.loc[coverage["regiao"].eq("SP")]
    assert not sp.empty
    assert float(sp["indefinido_pct"].max()) == 0.5
    assert "mail" in tokens["token"].tolist()


def test_relabel_script_helpers_generate_v3_columns() -> None:
    frame = pd.DataFrame(
        [
            {"texto_completo": "refat", "_source_region": "SP"},
            {"texto_completo": "medidor quebrado", "_source_region": "CE"},
        ]
    )

    out = relabel_frame(frame)
    report = coverage_report(out, duration_seconds=0.5)

    assert {"causa_canonica_v3", "causa_canonica_confidence"}.issubset(out.columns)
    assert report["rows"] == 2
    assert report["by_region"]["SP"]["rows"] == 1


def _severity_row(ordem: str, *, confidence: str) -> dict[str, object]:
    return {
        "ordem": ordem,
        "regiao": "SP",
        "causa_canonica": "autoleitura_cliente",
        "causa_canonica_confidence": confidence,
        "instalacao_hash": ordem,
        "flag_resolvido_com_refaturamento": False,
        "mes_ingresso": pd.Timestamp("2026-01-01"),
        "valor_fatura_reclamada_medio": 10.0,
    }


def _coverage_row(
    ordem: str,
    regiao: str,
    causa: str,
    confidence: str,
    keywords: str,
    assunto: str,
) -> dict[str, str]:
    return {
        "ordem": ordem,
        "regiao": regiao,
        "causa_canonica": causa,
        "causa_canonica_confidence": confidence,
        "topic_keywords": keywords,
        "assunto": assunto,
    }
