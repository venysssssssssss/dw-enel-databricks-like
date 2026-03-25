"""Pure business rules reused by Silver transformations and tests."""

from __future__ import annotations

from datetime import date
from math import asin, cos, radians, sin, sqrt
from typing import Any


ACF_A_TYPES = {
    "CORTE",
    "RELIGACAO",
    "SUBSTITUICAO_MEDIDOR",
    "INSTALACAO_MEDIDOR",
    "REGULARIZACAO_FRAUDE",
}
ACF_B_TYPES = {
    "INSPECAO_PROGRAMADA",
    "VERIFICACAO_MEDIDOR",
    "ATUALIZACAO_CADASTRAL_COM_MEDICAO",
    "REVISAO_LEITURA",
}
ACF_C_TYPES = {
    "ATUALIZACAO_CADASTRAL",
    "EMISSAO_SEGUNDA_VIA",
    "ALTERACAO_TITULARIDADE",
    "SOLICITACAO_HISTORICO",
}


def normalize_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = " ".join(value.strip().upper().split())
    return normalized or None


def parse_boolish(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "t", "yes", "sim", "s"}


def normalize_decimal_string(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    if not stripped:
        return None
    return stripped.replace(".", "").replace(",", ".") if "," in stripped else stripped


def classify_acf_asf_record(record: dict[str, Any]) -> str:
    tipo_servico = normalize_text(str(record.get("tipo_servico", ""))) or ""
    impacto_faturamento = parse_boolish(record.get("flag_impacto_faturamento"))
    risco = (
        parse_boolish(record.get("area_classificada_risco"))
        or int(record.get("historico_incidentes_12m") or 0) >= 2
        or normalize_text(record.get("tipo_instalacao")) in {"SUBESTACAO", "ALTA_TENSAO", "AREA_INDUSTRIAL_RISCO", "ZONA_RURAL_ISOLADA"}
        or not ("06:00" <= str(record.get("horario_agendado", "06:00")) <= "18:00")
        or parse_boolish(record.get("flag_risco_manual"))
    )
    if impacto_faturamento:
        if tipo_servico in ACF_A_TYPES:
            return "ACF_A"
        if tipo_servico in ACF_B_TYPES:
            return "ACF_B"
        return "ACF_C"
    return "ASF_RISCO" if risco else "ASF_FORA_RISCO"


def calculate_days_delay(
    planned_date: date | None,
    executed_date: date | None,
    *,
    reference_date: date | None = None,
) -> int:
    if planned_date is None:
        return 0
    comparison_date = reference_date or date.today()
    if executed_date is not None and executed_date > planned_date:
        return (executed_date - planned_date).days
    if executed_date is None and comparison_date > planned_date:
        return (comparison_date - planned_date).days
    return 0


def calculate_status_atraso(
    planned_date: date | None,
    executed_date: date | None,
    *,
    reference_date: date | None = None,
) -> str:
    if planned_date is None:
        return "SEM_PREVISAO"
    comparison_date = reference_date or date.today()
    if executed_date is not None and executed_date <= planned_date:
        return "NO_PRAZO"
    if executed_date is not None and executed_date > planned_date:
        return "ATRASADO"
    if comparison_date <= planned_date:
        return "PENDENTE_NO_PRAZO"
    return "PENDENTE_FORA_PRAZO"


def haversine_meters(lat1: float | None, lon1: float | None, lat2: float | None, lon2: float | None) -> float | None:
    if None in {lat1, lon1, lat2, lon2}:
        return None
    radius = 6_371_000
    lat1_r, lon1_r, lat2_r, lon2_r = map(radians, [lat1, lon1, lat2, lon2])
    delta_lat = lat2_r - lat1_r
    delta_lon = lon2_r - lon1_r
    value = sin(delta_lat / 2) ** 2 + cos(lat1_r) * cos(lat2_r) * sin(delta_lon / 2) ** 2
    return 2 * radius * asin(sqrt(value))
