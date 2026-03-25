"""Service for filtered exports."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any
from uuid import uuid4

from fastapi.responses import StreamingResponse

from src.api.config import get_api_settings
from src.api.schemas.common import ExportFormat
from src.api.schemas.exports import (
    ExportBaseRequest,
    ExportResponse,
)
from src.common.minio_client import MinIOClient


class ExportService:
    TABLE_BY_DOMAIN = {
        "notas": "gold.fato_notas_operacionais",
        "entregas": "gold.fato_entrega_fatura",
        "pagamentos": "gold.fato_pagamento",
        "metas": "gold.fato_metas",
        "efetividade": "gold.fato_efetividade",
    }

    def __init__(self, trino, minio: MinIOClient) -> None:
        self.trino = trino
        self.minio = minio
        self.settings = get_api_settings()

    async def export_domain(
        self,
        domain: str,
        filters: ExportBaseRequest,
        export_format: ExportFormat,
    ) -> ExportResponse:
        query = self.build_query(self.TABLE_BY_DOMAIN[domain], filters)
        results = await self.trino.execute(query)
        export_id = str(uuid4())
        file_path = self._write_file(export_id, results, export_format)
        key = f"{domain}/{file_path.name}"
        try:
            self.minio.ensure_bucket(self.settings.minio_exports_bucket)
            self.minio.upload_file(file_path, self.settings.minio_exports_bucket, key)
            download_url = self.minio.get_presigned_url(self.settings.minio_exports_bucket, key)
        except Exception:
            download_url = str(file_path)
        return ExportResponse(
            export_id=export_id,
            status="READY",
            download_url=download_url,
            row_count=len(results),
            format=export_format,
        )

    async def stream_domain(
        self,
        domain: str,
        filters: ExportBaseRequest,
        export_format: ExportFormat,
    ) -> StreamingResponse:
        query = self.build_query(self.TABLE_BY_DOMAIN[domain], filters)

        async def iterator():
            async for batch in self.trino.execute_streaming(query, batch_size=1000):
                for row in batch:
                    if export_format == ExportFormat.JSON:
                        yield json.dumps(row, ensure_ascii=True) + "\n"
                    else:
                        yield ",".join(str(value) for value in row.values()) + "\n"

        media_type = "application/json" if export_format == ExportFormat.JSON else "text/csv"
        return StreamingResponse(iterator(), media_type=media_type)

    def build_query(self, table: str, filters: ExportBaseRequest) -> str:
        conditions = [
            f"data between date '{filters.periodo_inicio}' and date '{filters.periodo_fim}'",
        ]
        if filters.distribuidora is not None:
            conditions.append(f"sk_distribuidora = {filters.distribuidora}")
        if filters.ut is not None:
            conditions.append(f"sk_ut = {filters.ut}")
        if filters.co is not None:
            conditions.append(f"sk_co = {filters.co}")
        if filters.base is not None:
            conditions.append(f"sk_base = {filters.base}")
        return f"select * from {table} where {' and '.join(conditions)}"

    def _write_file(
        self,
        export_id: str,
        rows: list[dict[str, Any]],
        export_format: ExportFormat,
    ) -> Path:
        suffix = f".{export_format.value}"
        with NamedTemporaryFile(delete=False, suffix=suffix, prefix=f"{export_id}_") as handle:
            path = Path(handle.name)
        if export_format == ExportFormat.JSON:
            path.write_text(json.dumps(rows, ensure_ascii=True, default=str), encoding="utf-8")
            return path
        if export_format == ExportFormat.PARQUET:
            path.write_text(json.dumps(rows, ensure_ascii=True, default=str), encoding="utf-8")
            return path
        fieldnames = list(rows[0].keys()) if rows else []
        with path.open("w", encoding="utf-8", newline="") as csv_handle:
            writer = csv.DictWriter(csv_handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        return path
