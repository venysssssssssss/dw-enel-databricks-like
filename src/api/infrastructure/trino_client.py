"""Asynchronous Trino client."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import httpx

from src.api.exceptions import TrinoError


class AsyncTrinoClient:
    def __init__(self, host: str, port: int, catalog: str, schema: str) -> None:
        self.base_url = f"http://{host}:{port}"
        self.catalog = catalog
        self.schema = schema
        self._client = httpx.AsyncClient(timeout=60.0)

    async def execute(self, query: str) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        async for batch in self.execute_streaming(query):
            rows.extend(batch)
        return rows

    async def execute_streaming(
        self,
        query: str,
        batch_size: int = 5000,
    ) -> AsyncIterator[list[dict[str, Any]]]:
        try:
            response = await self._client.post(
                f"{self.base_url}/v1/statement",
                content=query,
                headers={
                    "X-Trino-User": "enel",
                    "X-Trino-Catalog": self.catalog,
                    "X-Trino-Schema": self.schema,
                },
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise TrinoError(str(exc)) from exc

        result = response.json()
        columns = [column["name"] for column in result.get("columns", [])]

        while True:
            if "data" in result:
                rows = [dict(zip(columns, row, strict=False)) for row in result["data"]]
                for index in range(0, len(rows), batch_size):
                    yield rows[index : index + batch_size]
            next_uri = result.get("nextUri")
            if not next_uri:
                break
            next_response = await self._client.get(next_uri)
            next_response.raise_for_status()
            result = next_response.json()

    async def close(self) -> None:
        await self._client.aclose()


class InMemoryTrinoClient(AsyncTrinoClient):
    def __init__(self, fixtures: dict[str, list[dict[str, Any]]] | None = None) -> None:
        self.fixtures = fixtures or {}

    async def execute(self, query: str) -> list[dict[str, Any]]:  # type: ignore[override]
        return self.fixtures.get(query, [])

    async def execute_streaming(  # type: ignore[override]
        self,
        query: str,
        batch_size: int = 5000,
    ) -> AsyncIterator[list[dict[str, Any]]]:
        rows = self.fixtures.get(query, [])
        for index in range(0, len(rows), batch_size):
            yield rows[index : index + batch_size]

    async def close(self) -> None:  # type: ignore[override]
        return None
