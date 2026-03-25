"""Silver transformations for conforming master datasets."""

from __future__ import annotations

from src.transformation.base import BaseSilverTransformer


class _BaseCadastroTransformer(BaseSilverTransformer):
    def get_dedup_order(self) -> str:
        return "_ingested_at"

    def transform(self, df):  # type: ignore[override]
        from pyspark.sql.functions import trim, upper

        normalized = df
        for column_name in [name for name in df.columns if name.startswith("nome_") or name in {"endereco", "funcao", "equipe", "classe_consumo", "tipo_ligacao", "status_uc", "tipo_base", "tipo_instalacao"}]:
            normalized = normalized.withColumn(column_name, upper(trim(normalized[column_name])))
        return self.add_silver_metadata(normalized)


class CadastroDistribuidorasSilverTransformer(_BaseCadastroTransformer):
    def __init__(self, spark) -> None:
        super().__init__("cadastro_distribuidoras", spark)

    def get_dedup_keys(self) -> list[str]:
        return ["cod_distribuidora"]


class CadastroUTsSilverTransformer(_BaseCadastroTransformer):
    def __init__(self, spark) -> None:
        super().__init__("cadastro_uts", spark)

    def get_dedup_keys(self) -> list[str]:
        return ["cod_ut"]


class CadastroCOsSilverTransformer(_BaseCadastroTransformer):
    def __init__(self, spark) -> None:
        super().__init__("cadastro_cos", spark)

    def get_dedup_keys(self) -> list[str]:
        return ["cod_co"]


class CadastroBasesSilverTransformer(_BaseCadastroTransformer):
    def __init__(self, spark) -> None:
        super().__init__("cadastro_bases", spark)

    def get_dedup_keys(self) -> list[str]:
        return ["cod_base"]


class CadastroUCsSilverTransformer(_BaseCadastroTransformer):
    def __init__(self, spark) -> None:
        super().__init__("cadastro_ucs", spark)

    def get_dedup_keys(self) -> list[str]:
        return ["cod_uc"]


class CadastroInstalacoesSilverTransformer(_BaseCadastroTransformer):
    def __init__(self, spark) -> None:
        super().__init__("cadastro_instalacoes", spark)

    def get_dedup_keys(self) -> list[str]:
        return ["cod_instalacao"]


class CadastroColaboradoresSilverTransformer(_BaseCadastroTransformer):
    def __init__(self, spark) -> None:
        super().__init__("cadastro_colaboradores", spark)

    def get_dedup_keys(self) -> list[str]:
        return ["cod_colaborador"]


MASTER_TRANSFORMERS = {
    "cadastro_distribuidoras": CadastroDistribuidorasSilverTransformer,
    "cadastro_uts": CadastroUTsSilverTransformer,
    "cadastro_cos": CadastroCOsSilverTransformer,
    "cadastro_bases": CadastroBasesSilverTransformer,
    "cadastro_ucs": CadastroUCsSilverTransformer,
    "cadastro_instalacoes": CadastroInstalacoesSilverTransformer,
    "cadastro_colaboradores": CadastroColaboradoresSilverTransformer,
}
