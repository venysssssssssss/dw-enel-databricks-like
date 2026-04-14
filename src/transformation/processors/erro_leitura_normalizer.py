"""Normalization and text processing for erro de leitura complaints."""

from __future__ import annotations

import html
import re
import unicodedata
from dataclasses import dataclass

import pandas as pd


TEXT_COLUMNS = ("observacao_ordem", "devolutiva")


@dataclass(frozen=True, slots=True)
class EntityExtraction:
    telefones: tuple[str, ...]
    ceps: tuple[str, ...]
    protocolos: tuple[str, ...]
    datas: tuple[str, ...]
    instalacoes_mencionadas: tuple[str, ...]


def clean_text(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    text = html.unescape(str(value))
    text = re.sub(r"<br\s*/?>", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = unicodedata.normalize("NFKD", text)
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = text.casefold()
    text = re.sub(r"\s+", " ", text).strip()
    return text


def normalize_code(value: object) -> str | None:
    if value is None or pd.isna(value):
        return None
    text = str(value).strip().upper()
    if text.endswith(".0") and text[:-2].isdigit():
        text = text[:-2]
    return text or None


def extract_entities(text: str) -> EntityExtraction:
    telefones = tuple(sorted(set(re.findall(r"(?:\+?55\s*)?(?:\(?\d{2}\)?\s*)?9?\d{4}[-\s]?\d{4}", text))))
    ceps = tuple(sorted(set(re.findall(r"\b\d{5}-?\d{3}\b", text))))
    protocolos = tuple(sorted(set(re.findall(r"\b(?:protocolo|prot)\s*[:#-]?\s*(\d{6,})\b", text))))
    datas = tuple(sorted(set(re.findall(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b", text))))
    instalacoes = tuple(
        sorted(
            set(
                re.findall(
                    r"\b(?:uc|instalacao|instalação|inst)\s*[:#-]?\s*(\d{5,})\b",
                    text,
                )
            )
        )
    )
    return EntityExtraction(
        telefones=telefones,
        ceps=ceps,
        protocolos=protocolos,
        datas=datas,
        instalacoes_mencionadas=instalacoes,
    )


def infer_resolvido_com_refaturamento(status: str | None, devolutiva_clean: str) -> bool:
    status_text = clean_text(status)
    if "refatur" in devolutiva_clean:
        return True
    return "refatur" in status_text


def normalize_erro_leitura_frame(frame: pd.DataFrame) -> pd.DataFrame:
    required = {"ordem", "_source_region", "_sheet_name", "_data_type"}
    missing = sorted(required.difference(frame.columns))
    if missing:
        raise ValueError(f"Colunas obrigatorias ausentes na normalizacao de erro leitura: {missing}")

    normalized = frame.copy()
    for column in ["ordem", "instalacao", "grupo", "assunto", "status", "causa_raiz"]:
        if column in normalized.columns:
            normalized[column] = normalized[column].map(normalize_code)

    for column in TEXT_COLUMNS:
        raw_column = f"{column}_raw"
        if column not in normalized.columns:
            normalized[column] = ""
        normalized[raw_column] = normalized[column]
        normalized[column] = normalized[column].map(clean_text)

    normalized["texto_completo"] = (
        normalized["observacao_ordem"].fillna("") + " " + normalized["devolutiva"].fillna("")
    ).str.strip()
    entities = normalized["texto_completo"].map(extract_entities)
    normalized["telefones_extraidos"] = entities.map(lambda value: list(value.telefones))
    normalized["ceps_extraidos"] = entities.map(lambda value: list(value.ceps))
    normalized["protocolos_extraidos"] = entities.map(lambda value: list(value.protocolos))
    normalized["datas_extraidas"] = entities.map(lambda value: list(value.datas))
    normalized["instalacoes_mencionadas"] = entities.map(lambda value: list(value.instalacoes_mencionadas))
    normalized["has_causa_raiz_label"] = normalized.get("causa_raiz", pd.Series(index=normalized.index)).notna()
    normalized.loc[normalized["_source_region"].eq("SP"), "has_causa_raiz_label"] = False
    normalized["dt_ingresso"] = pd.to_datetime(normalized.get("dt_ingresso"), errors="coerce")
    normalized["flag_resolvido_com_refaturamento"] = normalized.apply(
        lambda row: infer_resolvido_com_refaturamento(row.get("status"), row.get("devolutiva", "")),
        axis=1,
    )
    normalized = normalized.sort_values(["ordem", "_source_region", "_sheet_name"])
    normalized = normalized.drop_duplicates(subset=["ordem", "_source_region"], keep="last")
    return normalized.reset_index(drop=True)
