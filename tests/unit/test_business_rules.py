from __future__ import annotations

from datetime import date

from src.transformation.processors.business_rules import (
    calculate_days_delay,
    calculate_status_atraso,
    classify_acf_asf_record,
    haversine_meters,
    normalize_decimal_string,
)


def test_classifies_acf_a() -> None:
    result = classify_acf_asf_record(
        {
            "tipo_servico": "CORTE",
            "flag_impacto_faturamento": True,
            "historico_incidentes_12m": 0,
            "area_classificada_risco": False,
            "tipo_instalacao": "RESIDENCIAL",
            "horario_agendado": "10:00",
            "flag_risco_manual": False,
        }
    )
    assert result == "ACF_A"


def test_classifies_asf_risco() -> None:
    result = classify_acf_asf_record(
        {
            "tipo_servico": "SERVICO_CAMPO",
            "flag_impacto_faturamento": False,
            "historico_incidentes_12m": 3,
            "area_classificada_risco": False,
            "tipo_instalacao": "RESIDENCIAL",
            "horario_agendado": "10:00",
            "flag_risco_manual": False,
        }
    )
    assert result == "ASF_RISCO"


def test_delay_calculation_for_pending_overdue() -> None:
    delay = calculate_days_delay(date(2026, 1, 1), None, reference_date=date(2026, 1, 10))
    status = calculate_status_atraso(date(2026, 1, 1), None, reference_date=date(2026, 1, 10))
    assert delay == 9
    assert status == "PENDENTE_FORA_PRAZO"


def test_haversine_returns_none_for_missing_coordinates() -> None:
    assert haversine_meters(None, -46.6, -23.5, -46.6) is None


def test_normalize_decimal_string() -> None:
    assert normalize_decimal_string("1.234,56") == "1234.56"
