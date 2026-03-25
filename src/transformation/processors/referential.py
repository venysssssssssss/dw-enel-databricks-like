"""Referential integrity validation helpers."""

from __future__ import annotations

from src.common.logging import get_logger

logger = get_logger(__name__)


def validate_referential_integrity(df_child, df_parent, fk_col: str, pk_col: str) -> int:
    orphans = df_child.join(df_parent, df_child[fk_col] == df_parent[pk_col], "left_anti")
    orphan_count = int(orphans.count())
    if orphan_count > 0:
        logger.warning("orphan_records", count=orphan_count, fk=fk_col, pk=pk_col)
    return orphan_count
