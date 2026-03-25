from __future__ import annotations

from src.common.sample_data import build_all_datasets


def test_build_all_datasets_contains_priority_sources() -> None:
    dataset_names = {dataset.name for dataset in build_all_datasets(100)}
    assert {"notas_operacionais", "entregas_fatura", "pagamentos", "metas_operacionais"}.issubset(dataset_names)


def test_notas_have_expected_columns() -> None:
    notas = next(dataset for dataset in build_all_datasets(10) if dataset.name == "notas_operacionais")
    assert {"cod_nota", "cod_uc", "tipo_servico", "data_alteracao"}.issubset(notas.rows[0].keys())
