"""Prepare RAG embedding training triplets from telemetry and feedback."""

from __future__ import annotations

import csv
import json
import random
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def load_telemetry(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}

    telemetry: dict[str, dict[str, Any]] = {}
    with open(path, encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                print(f"Ignorando telemetria inválida em {path}:{line_number}: {exc}")
                continue
            question_hash = row.get("question_hash")
            if question_hash:
                telemetry[str(question_hash)] = row
    return telemetry


def load_feedback(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}

    feedback: dict[str, str] = {}
    with open(path, encoding="utf-8") as file:
        reader = csv.DictReader(file)
        for row in reader:
            question_hash = row.get("question_hash")
            rating = (row.get("rating") or "").lower()
            if question_hash and rating in {"up", "down"}:
                feedback[question_hash] = rating
    return feedback


def _extract_anchors(sources: list[str]) -> list[str]:
    anchors: list[str] = []
    for source in sources:
        anchors.append(source.split("#", 1)[1] if "#" in source else source)
    return anchors


def _choose_other_anchor(all_anchors: list[str], selected: str, *, fallback: str) -> str:
    candidates = [anchor for anchor in all_anchors if anchor != selected]
    if not candidates:
        return fallback
    return random.choice(candidates)


def build_triplets(
    *,
    telemetry: dict[str, dict[str, Any]],
    feedback: dict[str, str],
    anchor_to_text: dict[str, str],
) -> list[dict[str, Any]]:
    all_anchors = list(anchor_to_text)
    triplets: list[dict[str, Any]] = []

    for question_hash, event in telemetry.items():
        question = event.get("question_preview")
        if not question:
            continue

        sources = event.get("extra", {}).get("sources", [])
        anchors = _extract_anchors(sources)
        if not anchors:
            continue

        primary_anchor = anchors[0]
        if primary_anchor not in anchor_to_text:
            continue

        rating = feedback.get(question_hash)
        if rating == "down":
            negative_anchor = primary_anchor
            positive_anchor = _choose_other_anchor(
                all_anchors,
                negative_anchor,
                fallback="visao-geral",
            )
            weight = 1.0
        else:
            positive_anchor = primary_anchor
            negative_anchor = _choose_other_anchor(
                all_anchors,
                positive_anchor,
                fallback="glossario",
            )
            weight = 1.0 if rating == "up" or event.get("cache_hit") else 0.5

        if positive_anchor not in anchor_to_text or negative_anchor not in anchor_to_text:
            continue

        triplets.append(
            {
                "query": str(question),
                "positive": anchor_to_text[positive_anchor][:800],
                "negative": anchor_to_text[negative_anchor][:800],
                "weight": weight,
            }
        )
    return triplets


def main() -> None:
    from src.data_plane.store import DataStore

    base_dir = Path(__file__).resolve().parent.parent
    telemetry_path = base_dir / "data/rag/telemetry.jsonl"
    feedback_path = base_dir / "data/rag/feedback.csv"
    output_path = base_dir / "data/rag/training_triplets.jsonl"

    store = DataStore()
    anchor_to_text = {card.anchor: card.text for card in store.cards()}
    if not anchor_to_text:
        print("Erro: nenhum card carregado. Execute o warmup do cache primeiro.")
        return

    triplets = build_triplets(
        telemetry=load_telemetry(telemetry_path),
        feedback=load_feedback(feedback_path),
        anchor_to_text=anchor_to_text,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as file:
        for triplet in triplets:
            file.write(json.dumps(triplet, ensure_ascii=False) + "\n")

    print(f"{len(triplets)} tripletos de treino extraídos com textos literais.")
    print(f"Salvo em {output_path.relative_to(base_dir)}")


if __name__ == "__main__":
    main()
