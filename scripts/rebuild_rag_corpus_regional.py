"""Rebuild idempotente do corpus RAG com escopo regional CE/SP."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.rag.config import load_rag_config  # noqa: E402
from src.rag.ingestion import build_corpus  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Rebuild do corpus RAG regional CE/SP")
    parser.add_argument(
        "--regional-scope",
        default="CE+SP",
        choices=["CE", "SP", "CE+SP"],
        help="Escopo regional para geração dos data cards.",
    )
    parser.add_argument(
        "--no-rebuild",
        action="store_true",
        help="Não apaga coleção anterior, apenas upsert incremental.",
    )
    args = parser.parse_args()

    os.environ["RAG_REGIONAL_SCOPE"] = args.regional_scope
    config = load_rag_config()
    stats = build_corpus(config, rebuild=not args.no_rebuild)

    manifest = {
        "ts": datetime.now(UTC).isoformat(),
        "regional_scope": args.regional_scope,
        "chromadb_path": str(config.chromadb_path),
        "collection_name": config.collection_name,
        "embedding_model": config.embedding_model,
        "stats": stats.as_dict(),
    }
    manifest_path = Path("data/rag/corpus_manifest.json")
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
