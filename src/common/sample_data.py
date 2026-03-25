"""Synthetic data generators aligned with the documented business contracts."""

from __future__ import annotations

import csv
import random
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from src.common.config import get_settings


SERVICE_TYPES = [
    "CORTE",
    "RELIGACAO",
    "SUBSTITUICAO_MEDIDOR",
    "INSPECAO_PROGRAMADA",
    "VERIFICACAO_MEDIDOR",
    "ATUALIZACAO_CADASTRAL",
]
STATUS_VALUES = [
    "CRIADA",
    "ATRIBUIDA",
    "EM_CAMPO",
    "EXECUTADA",
    "FECHADA",
    "DEVOLVIDA",
    "CANCELADA",
    "REABERTA",
]


@dataclass(frozen=True, slots=True)
class DatasetDefinition:
    name: str
    rows: list[dict[str, Any]]


def _format_date(value: date | None) -> str:
    return "" if value is None else value.strftime("%d/%m/%Y")


def _format_timestamp(value: datetime) -> str:
    return value.strftime("%d/%m/%Y %H:%M:%S")


def build_notas_operacionais(rows: int, *, seed: int = 42) -> DatasetDefinition:
    rng = random.Random(seed)
    base_date = date(2026, 1, 1)
    dataset_rows: list[dict[str, Any]] = []
    for index in range(rows):
        created_at = base_date + timedelta(days=index % 90)
        planned_at = created_at + timedelta(days=rng.randint(1, 7))
        executed_at = None if index % 6 == 0 else planned_at + timedelta(days=index % 4)
        updated_at = datetime.combine(created_at, datetime.min.time()) + timedelta(hours=index % 23)
        dataset_rows.append(
            {
                "cod_nota": str(100000 + index),
                "cod_uc": str(200000 + (index % 500)),
                "cod_instalacao": str(300000 + (index % 400)),
                "cod_distribuidora": str(10 + (index % 4)),
                "cod_ut": str(100 + (index % 8)),
                "cod_co": str(1000 + (index % 16)),
                "cod_base": str(10000 + (index % 24)),
                "cod_lote": str(900 + (index % 12)),
                "tipo_servico": SERVICE_TYPES[index % len(SERVICE_TYPES)],
                "flag_impacto_faturamento": "true" if index % 2 == 0 else "false",
                "area_classificada_risco": "true" if index % 9 == 0 else "false",
                "historico_incidentes_12m": str(index % 4),
                "tipo_instalacao": "SUBESTACAO" if index % 17 == 0 else "RESIDENCIAL",
                "horario_agendado": f"{6 + (index % 12):02d}:00",
                "flag_risco_manual": "true" if index % 29 == 0 else "false",
                "data_criacao": _format_date(created_at),
                "data_prevista": _format_date(planned_at),
                "data_execucao": _format_date(executed_at),
                "data_alteracao": _format_timestamp(updated_at),
                "status": STATUS_VALUES[index % len(STATUS_VALUES)],
                "cod_colaborador": str(4000 + (index % 40)),
                "latitude": f"{-23.50 + rng.uniform(-0.8, 0.8):.6f}",
                "longitude": f"{-46.60 + rng.uniform(-0.8, 0.8):.6f}",
            }
        )
    return DatasetDefinition(name="notas_operacionais", rows=dataset_rows)


def build_entregas_fatura(rows: int, *, seed: int = 43) -> DatasetDefinition:
    rng = random.Random(seed)
    base_date = date(2026, 1, 1)
    dataset_rows: list[dict[str, Any]] = []
    for index in range(rows):
        emission = base_date + timedelta(days=index % 60)
        delivery = emission + timedelta(days=rng.randint(1, 8))
        due_date = emission + timedelta(days=10)
        lat = -23.50 + rng.uniform(-0.2, 0.2)
        lon = -46.60 + rng.uniform(-0.2, 0.2)
        dataset_rows.append(
            {
                "cod_entrega": str(500000 + index),
                "cod_fatura": str(600000 + index),
                "cod_uc": str(200000 + (index % 500)),
                "cod_distribuidora": str(10 + (index % 4)),
                "data_emissao": _format_date(emission),
                "data_vencimento": _format_date(due_date),
                "data_entrega": _format_date(delivery if index % 11 != 0 else None),
                "lat_entrega": f"{lat:.6f}",
                "lon_entrega": f"{lon:.6f}",
                "lat_uc": f"{lat + rng.uniform(-0.0004, 0.0004):.6f}",
                "lon_uc": f"{lon + rng.uniform(-0.0004, 0.0004):.6f}",
                "flag_entregue": "true" if index % 11 != 0 else "false",
                "data_registro": _format_timestamp(
                    datetime.combine(emission, datetime.min.time()) + timedelta(hours=index % 20)
                ),
            }
        )
    return DatasetDefinition(name="entregas_fatura", rows=dataset_rows)


def build_pagamentos(rows: int, *, seed: int = 44) -> DatasetDefinition:
    rng = random.Random(seed)
    base_date = date(2026, 1, 1)
    dataset_rows: list[dict[str, Any]] = []
    for index in range(rows):
        due_date = base_date + timedelta(days=index % 90)
        paid_date = None if index % 5 == 0 else due_date + timedelta(days=index % 25)
        amount = round(75 + rng.uniform(0, 400), 2)
        paid_amount = amount if paid_date is not None else None
        dataset_rows.append(
            {
                "cod_pagamento": str(700000 + index),
                "cod_fatura": str(600000 + index),
                "cod_uc": str(200000 + (index % 500)),
                "valor_fatura": f"{amount:.2f}".replace(".", ","),
                "valor_pago": "" if paid_amount is None else f"{paid_amount:.2f}".replace(".", ","),
                "data_vencimento": _format_date(due_date),
                "data_pagamento": _format_date(paid_date),
                "forma_pagamento": "PIX" if index % 3 == 0 else "BOLETO",
                "data_processamento": _format_timestamp(
                    datetime.combine(due_date, datetime.min.time()) + timedelta(hours=12)
                ),
            }
        )
    return DatasetDefinition(name="pagamentos", rows=dataset_rows)


def _build_master_rows(rows: int, prefix: str, fields: dict[str, Any]) -> list[dict[str, Any]]:
    dataset_rows: list[dict[str, Any]] = []
    for index in range(rows):
        row = {
            key: (str(value(index)) if callable(value) else str(value))
            for key, value in fields.items()
        }
        row[f"cod_{prefix}"] = str(index + 1)
        dataset_rows.append(row)
    return dataset_rows


def build_master_datasets(rows: int) -> list[DatasetDefinition]:
    return [
        DatasetDefinition(
            "cadastro_distribuidoras",
            _build_master_rows(
                4,
                "distribuidora",
                {"nome_distribuidora": lambda index: f"ENEL {['SP', 'RJ', 'CE', 'GO'][index % 4]}", "uf": lambda index: ['SP', 'RJ', 'CE', 'GO'][index % 4]},
            ),
        ),
        DatasetDefinition(
            "cadastro_uts",
            _build_master_rows(
                max(rows // 100, 8),
                "ut",
                {
                    "cod_distribuidora": lambda index: 1 + (index % 4),
                    "nome_ut": lambda index: f"UT {index + 1}",
                },
            ),
        ),
        DatasetDefinition(
            "cadastro_cos",
            _build_master_rows(
                max(rows // 80, 16),
                "co",
                {
                    "cod_ut": lambda index: 1 + (index % 8),
                    "nome_co": lambda index: f"CO {index + 1}",
                },
            ),
        ),
        DatasetDefinition(
            "cadastro_bases",
            _build_master_rows(
                max(rows // 60, 24),
                "base",
                {
                    "cod_co": lambda index: 1 + (index % 16),
                    "nome_base": lambda index: f"BASE {index + 1}",
                    "tipo_base": lambda index: "POLO" if index % 5 == 0 else "BASE",
                },
            ),
        ),
        DatasetDefinition(
            "cadastro_ucs",
            _build_master_rows(
                max(rows, 500),
                "uc",
                {
                    "cod_base": lambda index: 1 + (index % 24),
                    "classe_consumo": lambda index: ["RESIDENCIAL", "COMERCIAL", "INDUSTRIAL"][index % 3],
                    "tipo_ligacao": lambda index: ["MONOFASICA", "BIFASICA", "TRIFASICA"][index % 3],
                    "status_uc": lambda index: "ATIVA" if index % 7 != 0 else "SUSPENSA",
                },
            ),
        ),
        DatasetDefinition(
            "cadastro_instalacoes",
            _build_master_rows(
                max(rows, 500),
                "instalacao",
                {
                    "cod_uc": lambda index: 1 + (index % max(rows, 500)),
                    "endereco": lambda index: f"Rua {index + 1}, 100",
                    "tipo_instalacao": lambda index: "RESIDENCIAL" if index % 9 else "SUBESTACAO",
                },
            ),
        ),
        DatasetDefinition(
            "cadastro_colaboradores",
            _build_master_rows(
                max(rows // 30, 40),
                "colaborador",
                {
                    "nome_colaborador": lambda index: f"Colaborador {index + 1}",
                    "equipe": lambda index: f"Equipe {1 + (index % 6)}",
                    "funcao": lambda index: "TECNICO_CAMPO" if index % 2 == 0 else "SUPERVISOR",
                },
            ),
        ),
        DatasetDefinition(
            "metas_operacionais",
            [
                {
                    "cod_distribuidora": str(1 + (index % 4)),
                    "cod_ut": str(1 + (index % 8)),
                    "cod_co": str(1 + (index % 16)),
                    "cod_base": str(1 + (index % 24)),
                    "indicador": "EFETIVIDADE",
                    "mes_referencia": f"2026-{1 + (index % 12):02d}",
                    "valor_meta": str(1000 + index * 10),
                    "valor_realizado": str(800 + index * 8),
                }
                for index in range(max(rows // 30, 24))
            ],
        ),
    ]


def build_all_datasets(rows: int = 1000) -> list[DatasetDefinition]:
    return [
        build_notas_operacionais(rows),
        build_entregas_fatura(rows),
        build_pagamentos(rows),
        *build_master_datasets(rows),
    ]


def write_dataset(dataset: DatasetDefinition, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    file_path = output_dir / f"{dataset.name}.csv"
    fieldnames = list(dataset.rows[0].keys()) if dataset.rows else []
    with file_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter=";")
        writer.writeheader()
        writer.writerows(dataset.rows)
    return file_path


def generate_sample_files(rows: int = 1000, output_dir: Path | None = None) -> list[Path]:
    settings = get_settings()
    resolved_output_dir = output_dir or settings.sample_data_path
    return [write_dataset(dataset, resolved_output_dir) for dataset in build_all_datasets(rows)]
