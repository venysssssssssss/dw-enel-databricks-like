"""Bronze ingestion for ENEL complaint description Excel workbooks."""

from __future__ import annotations

import argparse
import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pandas as pd

from src.common.config import get_settings
from src.common.contracts import SourceConfig
from src.ingestion.base import BaseIngestor
from src.ingestion.config_loader import load_source_config

if TYPE_CHECKING:
    from pyspark.sql import DataFrame, SparkSession
else:  # pragma: no cover
    DataFrame = Any
    SparkSession = Any


CANONICAL_COLUMNS = {
    "GRUPO": "grupo",
    "ORDEM": "ordem",
    "ASSUNTO": "assunto",
    "INSTALACAO": "instalacao",
    "DT. INGRESSO": "dt_ingresso",
    "OBSERVAÇÃO ORDEM": "observacao_ordem",
    "Status": "status",
    "DEVOLUTIVA": "devolutiva",
    "Causa Raiz": "causa_raiz",
}


@dataclass(frozen=True, slots=True)
class WorkbookSummary:
    source_file: str
    source_region: str
    sheet_name: str
    data_type: str
    rows: int


def derive_source_region(file_path: Path) -> str:
    upper_name = file_path.name.upper()
    if "TRATADO TRIMESTRE_ORDENS" in upper_name or "BASE N1" in upper_name:
        return "SP"
    return "CE"


def classify_sheet(sheet_name: str, file_path: Path) -> str:
    normalized = sheet_name.strip().casefold()
    if derive_source_region(file_path) == "SP" or normalized == "base n1":
        return "base_n1_sp"
    if "erro" in normalized and "leitura" in normalized:
        return "erro_leitura"
    return "reclamacao_total"


def _source_hash(row: pd.Series, source_file: str, sheet_name: str) -> str:
    values = [source_file, sheet_name]
    values.extend(str(row.get(column, "")) for column in CANONICAL_COLUMNS.values())
    return hashlib.sha256("||".join(values).encode("utf-8")).hexdigest()


def read_workbook(file_path: Path) -> tuple[pd.DataFrame, list[WorkbookSummary]]:
    excel = pd.ExcelFile(file_path)
    frames: list[pd.DataFrame] = []
    summaries: list[WorkbookSummary] = []
    source_region = derive_source_region(file_path)
    for sheet_name in excel.sheet_names:
        raw_frame = pd.read_excel(file_path, sheet_name=sheet_name, dtype=str)
        raw_frame = raw_frame.rename(columns=CANONICAL_COLUMNS)
        for column in CANONICAL_COLUMNS.values():
            if column not in raw_frame.columns:
                raw_frame[column] = None
        frame = raw_frame[list(CANONICAL_COLUMNS.values())].copy()
        frame["_sheet_name"] = sheet_name
        frame["_data_type"] = classify_sheet(sheet_name, file_path)
        frame["_source_region"] = source_region
        frame["_source_file"] = file_path.name
        frame["_source_hash"] = frame.apply(lambda row: _source_hash(row, file_path.name, sheet_name), axis=1)
        frames.append(frame)
        summaries.append(
            WorkbookSummary(
                source_file=file_path.name,
                source_region=source_region,
                sheet_name=sheet_name,
                data_type=classify_sheet(sheet_name, file_path),
                rows=len(frame),
            )
        )
    if not frames:
        return pd.DataFrame(columns=[*CANONICAL_COLUMNS.values(), "_sheet_name", "_data_type"]), summaries
    return pd.concat(frames, ignore_index=True), summaries


def read_excel_directory(input_dir: Path) -> tuple[pd.DataFrame, list[WorkbookSummary]]:
    files = sorted(input_dir.glob("*.xlsx"))
    if not files:
        raise FileNotFoundError(f"Nenhum arquivo .xlsx encontrado em {input_dir}.")
    frames: list[pd.DataFrame] = []
    summaries: list[WorkbookSummary] = []
    for file_path in files:
        frame, workbook_summaries = read_workbook(file_path)
        frames.append(frame)
        summaries.extend(workbook_summaries)
    return pd.concat(frames, ignore_index=True), summaries


class DescricoesEnelIngestor(BaseIngestor):
    """Spark-compatible ingestor for the unified Bronze table."""

    def __init__(self, source_config: SourceConfig, spark: SparkSession, input_dir: Path | None = None) -> None:
        super().__init__(source_config, spark)
        self.input_dir = input_dir or self.resolve_source_path()

    def extract(self) -> DataFrame:
        frame, summaries = read_excel_directory(self.input_dir)
        self.logger.info(
            "descricoes_enel_excel_loaded",
            files=len({summary.source_file for summary in summaries}),
            sheets=len(summaries),
            rows=len(frame),
        )
        return self.spark.createDataFrame(frame.astype(object).where(pd.notna(frame), None))

    def _add_technical_metadata(self, df: DataFrame) -> DataFrame:
        from pyspark.sql.functions import current_date, current_timestamp, lit

        return (
            df.withColumn("_run_id", lit(self.run_id))
            .withColumn("_ingested_at", current_timestamp())
            .withColumn("_partition_date", current_date())
        )

    def _bronze_table_name(self) -> str:
        return "nessie.bronze.descricoes_reclamacoes"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, default=None)
    parser.add_argument("--dry-run", action="store_true", help="Apenas contabiliza arquivos/guias sem escrever Bronze.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    settings = get_settings()
    input_dir = args.input_dir or settings.project_root_path / "DESCRICOES_ENEL"
    if args.dry_run:
        _, summaries = read_excel_directory(input_dir)
        for summary in summaries:
            print(
                f"{summary.source_region}|{summary.data_type}|"
                f"{summary.source_file}|{summary.sheet_name}|{summary.rows}"
            )
        return 0

    from src.common.spark_session import create_spark_session

    config = load_source_config("descricoes_enel")
    result = DescricoesEnelIngestor(config, create_spark_session(memory="2g"), input_dir=input_dir).execute()
    print(f"{result.source_name}:{result.rows_ingested}:{result.status}:{result.run_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
