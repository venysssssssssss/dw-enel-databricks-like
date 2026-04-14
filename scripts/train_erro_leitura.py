"""Train local erro de leitura topic and classifier artifacts."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from src.ml.features.text_embeddings import TextEmbeddingBuilder
from src.ml.models.erro_leitura_classifier import ErroLeituraClassifierTrainer
from src.ml.models.erro_leitura_topic_model import ErroLeituraTopicModelTrainer


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("data/silver/erro_leitura_normalizado.csv"))
    parser.add_argument("--output-dir", type=Path, default=Path("data/model_registry/erro_leitura"))
    parser.add_argument(
        "--include-total",
        action="store_true",
        help="Inclui reclamacao_total no treino exploratorio. Por padrao usa apenas erro_leitura/base_n1_sp.",
    )
    parser.add_argument("--sample-size", type=int, default=None, help="Amostra deterministica para treino rapido.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    frame = pd.read_csv(args.input, dtype=str, low_memory=False)
    frame = _filter_training_frame(frame, include_total=args.include_total)
    if args.sample_size is not None and len(frame) > args.sample_size:
        frame = frame.sample(n=args.sample_size, random_state=42).sort_index()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    embedding_result = TextEmbeddingBuilder().build(frame)
    embeddings_path = args.output_dir / "embeddings.csv"
    embedding_result.frame.to_csv(embeddings_path, index=False)

    topics = ErroLeituraTopicModelTrainer(min_topic_size=5).train(frame)
    topics.assignments.to_csv(args.output_dir / "topic_assignments.csv", index=False)
    topics.taxonomy.to_json(args.output_dir / "topic_taxonomy.json", orient="records", force_ascii=True)

    training = ErroLeituraClassifierTrainer().train(frame)
    pd.DataFrame(
        [
            {
                "macro_f1": training.macro_f1,
                "backend": training.backend,
                "rows_used": len(frame),
                "data_types": ",".join(sorted(frame.get("_data_type", pd.Series(dtype=str)).dropna().unique())),
            }
        ]
    ).to_csv(
        args.output_dir / "classifier_metrics.csv",
        index=False,
    )
    print(f"erro_leitura:rows={len(frame)}:topics={len(topics.taxonomy)}:macro_f1={training.macro_f1:.4f}")
    return 0


def _filter_training_frame(frame: pd.DataFrame, *, include_total: bool) -> pd.DataFrame:
    if include_total or "_data_type" not in frame.columns:
        return frame.reset_index(drop=True)
    data_types = {"erro_leitura", "base_n1_sp"}
    filtered = frame.loc[frame["_data_type"].isin(data_types)].copy()
    if filtered.empty:
        raise ValueError("Nenhuma linha erro_leitura/base_n1_sp encontrada para treino.")
    return filtered.reset_index(drop=True)


if __name__ == "__main__":
    raise SystemExit(main())
