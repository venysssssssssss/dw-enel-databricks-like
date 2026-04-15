"""CLI para indexar o corpus RAG no ChromaDB.

Uso:
    python scripts/build_rag_corpus.py --rebuild
    python scripts/build_rag_corpus.py --download-model
    python scripts/build_rag_corpus.py --stats
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.rag.config import load_rag_config  # noqa: E402
from src.rag.ingestion import build_corpus, discover_files  # noqa: E402


_HF_URL_TEMPLATE = "https://huggingface.co/{repo}/resolve/main/{file}"


def cmd_build(rebuild: bool) -> int:
    config = load_rag_config()
    print(f"[rag] indexando corpus em {config.chromadb_path}")
    print(f"[rag] roots: {[str(r) for r in config.corpus_roots]}")
    try:
        stats = build_corpus(config, rebuild=rebuild)
    except RuntimeError as exc:
        print(f"[erro] {exc}")
        return 2
    print(json.dumps(stats.as_dict(), indent=2, ensure_ascii=False))
    return 0


def cmd_stats() -> int:
    config = load_rag_config()
    files = discover_files(config.corpus_roots)
    print(f"[rag] arquivos descobertos: {len(files)}")
    for f in files[:20]:
        print(f"  - {f.relative_to(ROOT) if ROOT in f.parents else f}")
    if len(files) > 20:
        print(f"  ... (+{len(files) - 20})")
    return 0


def cmd_download_model() -> int:
    config = load_rag_config()
    target_dir = Path("data/rag/models")
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / config.model_file
    if target.exists():
        print(f"[rag] modelo já existe: {target}")
        return 0
    url = _HF_URL_TEMPLATE.format(repo=config.model_repo, file=config.model_file)
    print(f"[rag] baixando {config.model_repo}/{config.model_file}")
    print(f"[rag]  → {target}  ({url})")
    try:
        _download(url, target)
    except Exception as exc:  # pragma: no cover - rede
        print(f"[erro] download falhou: {exc}")
        print("[dica] baixe manualmente e coloque em data/rag/models/ ou defina RAG_MODEL_PATH")
        return 3
    size_mb = target.stat().st_size / (1024 * 1024)
    print(f"[rag] ok — {size_mb:.1f} MB")
    return 0


def _download(url: str, dst: Path) -> None:
    with urllib.request.urlopen(url, timeout=600) as resp, dst.open("wb") as fh:
        total = int(resp.headers.get("Content-Length", 0))
        read = 0
        chunk = 1024 * 256
        while True:
            buf = resp.read(chunk)
            if not buf:
                break
            fh.write(buf)
            read += len(buf)
            if total:
                pct = 100 * read / total
                print(f"  {read / (1024*1024):.1f} / {total / (1024*1024):.1f} MB ({pct:.1f}%)", end="\r")
        print()


def main() -> int:
    parser = argparse.ArgumentParser(description="Indexa o corpus RAG ENEL")
    parser.add_argument("--rebuild", action="store_true", help="recria a coleção do zero")
    parser.add_argument("--stats", action="store_true", help="apenas lista arquivos")
    parser.add_argument(
        "--download-model",
        action="store_true",
        help="baixa o modelo GGUF default em data/rag/models/",
    )
    args = parser.parse_args()

    if args.download_model:
        return cmd_download_model()
    if args.stats:
        return cmd_stats()
    return cmd_build(rebuild=args.rebuild)


if __name__ == "__main__":
    sys.exit(main())
