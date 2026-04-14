"""Semi-supervised classifier for erro de leitura root causes.

Taxonomy v2 — construida a partir de inspecao empirica dos textos CE e SP.
Objetivo: eliminar o bucket "OUTROS" dominante em SP e entregar uma estrutura
de causa-raiz plenamente acionavel para tomada de decisao operacional.

Estrutura:
  - `TAXONOMY`: dicionario `classe → {description, category, severity, keywords,
    negatives, patterns_regex}`. `weight` default = 1.0, palavras criticas podem
    ter `weight` explicito via tupla `(termo, peso)`.
  - Scoring: soma dos pesos dos termos encontrados, penalidade por `negatives`.
  - Normalizacao de texto: casefold + remocao de acentos + colapso whitespace.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, f1_score
from sklearn.model_selection import TimeSeriesSplit
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import LabelEncoder

from src.ml.features.text_embeddings import TextEmbeddingBuilder


KeywordWeight = str | tuple[str, float]


@dataclass(frozen=True, slots=True)
class TaxonomyEntry:
    description: str
    category: str
    severity: str  # critical | high | medium | low
    keywords: tuple[KeywordWeight, ...]
    patterns: tuple[str, ...] = ()
    negatives: tuple[str, ...] = ()


TAXONOMY: dict[str, TaxonomyEntry] = {
    "digitacao": TaxonomyEntry(
        description="Digitacao ou transcricao incorreta da leitura pelo leiturista",
        category="processo_leitura",
        severity="high",
        keywords=(
            ("digitacao", 3.0),
            ("digitada errada", 3.0),
            ("numero errado", 2.5),
            ("leitura errada", 2.0),
            ("valor incorreto", 2.0),
            ("leitura incorreta", 2.0),
            ("inverteu", 2.0),
            ("invertida", 2.0),
            "erro de transcricao",
            "erro do leiturista",
            "transposicao",
        ),
        patterns=(
            r"\bleiturista\s+(registrou|anotou|digitou)\s+(errado|incorret)",
            r"\bnumero(s)?\s+(errado|incorret|trocad)",
        ),
    ),
    "leitura_estimada_media": TaxonomyEntry(
        description="Faturamento por media devido a impedimento ou ausencia de leitura",
        category="faturamento_por_media",
        severity="critical",
        keywords=(
            ("faturamento por media", 3.5),
            ("por media", 2.5),
            ("leitura estimada", 3.0),
            ("estimada", 2.0),
            ("plurimensal", 2.5),
            ("sem leitura", 2.0),
            ("leitura nao realizada", 2.5),
            ("calculo de m", 2.0),
            "media de consumo",
            "bimestral",
        ),
        patterns=(
            r"\baplicac[aã]o\s+(devida|indevida)\s+de\s+m[eé]dia",
            r"\bfatura(mento)?\s+por\s+m[eé]dia",
        ),
    ),
    "impedimento_acesso": TaxonomyEntry(
        description="Leiturista sem acesso fisico ao medidor (portao fechado, animal, cadeado)",
        category="acesso_fisico",
        severity="high",
        keywords=(
            ("impedimento de leitura", 3.5),
            ("impedimento", 2.5),
            ("nao da acesso", 3.0),
            ("sem acesso", 2.5),
            ("acesso negado", 3.0),
            ("portao fechado", 2.5),
            ("portao trancado", 2.5),
            ("cachorro", 1.5),
            ("cadeado", 1.5),
            ("dificil acesso", 2.0),
            ("local de dificil", 2.0),
            "centro de medicao",
            "morador ausente",
        ),
        patterns=(
            r"\bn[aã]o\s+(da|permite|permitiu)\s+acesso",
            r"\bim?pedim?(ento)?\s+de\s+leitura",
        ),
        negatives=("tenho acesso", "com acesso", "tem acesso"),
    ),
    "medidor_danificado": TaxonomyEntry(
        description="Problemas fisicos no medidor (visor embacado, quebrado, travado)",
        category="equipamento",
        severity="high",
        keywords=(
            ("medidor danificado", 3.5),
            ("medidor quebrado", 3.5),
            ("medidor com defeito", 3.0),
            ("visor embacado", 3.0),
            ("tampa embacada", 2.5),
            ("visor", 1.5),
            ("defeito", 1.8),
            ("aferido", 1.5),
            ("aferica", 1.5),
            ("laudo", 1.5),
            "medidor travado",
            "medidor parado",
        ),
        patterns=(
            r"\bmedidor\s+(queimado|quebrad|com\s+defeito|danific)",
            r"\blaudo\s+da\s+aferic",
        ),
    ),
    "autoleitura_cliente": TaxonomyEntry(
        description="Cliente contesta com foto/video/autoleitura ou apresenta leitura propria (forte em SP)",
        category="contestacao_cliente",
        severity="high",
        keywords=(
            ("autoleitura", 3.5),
            ("foto da leitura", 3.0),
            ("foto do medidor", 3.0),
            ("video do medidor", 3.0),
            ("evidencia", 2.0),
            ("imagem", 1.5),
            ("foto apresentada", 2.5),
            ("cliente informa numero", 2.0),
            ("cliente apresenta leitura", 3.0),
            ("leitura apresentada", 2.5),
            ("passa a leitura", 2.5),
            ("informa a leitura", 2.5),
            ("leitura real", 2.5),
            ("leitura do dia", 2.0),
            ("leitura correta", 2.0),
            ("leitura do relogio", 2.5),
            ("leitura atual", 1.5),
            ("leitura registrada em fatura", 1.5),
            "cliente fez a leitura",
            "encaminhou video",
            "encaminhou foto",
            "anexou foto",
        ),
        patterns=(
            r"\bfoto\s+(do|da)\s+(medid|leitur)",
            r"\bv[ií]deo\s+(do|da)\s+medid",
            r"\bauto\s*leitura\b",
            r"\bcliente\s+(apresenta|informa|passa|encaminh|relata)\s+(a\s+)?leitura",
        ),
    ),
    "consumo_elevado_revisao": TaxonomyEntry(
        description="Cliente contesta consumo alto / pede revisao sem evidencia especifica",
        category="contestacao_cliente",
        severity="medium",
        keywords=(
            ("revisao de fatura", 2.5),
            ("revisar fatura", 2.5),
            ("revisao da fatura", 2.5),
            ("analise de conta", 2.0),
            ("analise da fatura", 2.0),
            ("analise da conta", 2.0),
            ("consumo elevado", 2.5),
            ("valor muito acima", 2.5),
            ("valor elevado", 2.0),
            ("fatura alta", 2.0),
            ("conta alta", 2.0),
            ("reclama do valor", 2.0),
            ("contestar", 1.8),
            ("contestacao", 1.8),
            ("variacao", 1.2),
            ("fora da media", 2.0),
            ("valor acima", 2.0),
            ("nao aceita", 1.2),
            "acima da media",
            "saiu da media",
        ),
        patterns=(
            r"\bconsumo\s+(muito\s+)?(alt|elevad)",
            r"\brevis[aã]o\s+(de|da)\s+fatura",
            r"\banal[ií]se\s+(de|da)\s+(conta|fatura)",
        ),
    ),
    "compensacao_gd": TaxonomyEntry(
        description="Geracao distribuida — compensacao/rateio de energia injetada errada",
        category="geracao_distribuida",
        severity="critical",
        keywords=(
            ("gd", 2.5),
            ("geracao distribuida", 3.5),
            ("energia injetada", 3.0),
            ("compensacao", 2.5),
            ("saldo de rateio", 3.0),
            ("creditos de energia", 2.5),
            ("inversao", 2.0),
            ("energia gerada", 2.0),
            ("mini gerador", 2.0),
            "solar",
            "fotovoltaic",
        ),
        patterns=(
            r"\bcompensac[aã]o\s+de\s+energia",
            r"\binvers[aã]o\s+de\s+(consumo|energia)",
        ),
    ),
    "refaturamento_corretivo": TaxonomyEntry(
        description="Ordem resolvida via refaturamento (procedente)",
        category="resolucao",
        severity="medium",
        keywords=(
            ("refaturamento", 3.0),
            ("refaturar", 2.5),
            ("refatur", 2.0),
            ("fatura corrigida", 2.5),
            ("ajuste da leitura", 2.5),
            ("ajuste da conta", 2.5),
            ("ajuste de fatura", 2.5),
            ("nota de credito", 2.0),
            ("estorno", 2.0),
            ("fatura cancelada", 2.5),
            "cobranca cancelada",
        ),
        patterns=(
            r"\brefatur(ad|ament|a\s)",
            r"\bfatura\s+ajustad",
        ),
    ),
    "cobranca_indevida": TaxonomyEntry(
        description="Multa, taxa ou produto indevido na fatura (crefaz, religacao, etc)",
        category="faturamento",
        severity="high",
        keywords=(
            ("cobranca indevida", 3.5),
            ("cobranca multa", 2.5),
            ("autoreligacao", 3.0),
            ("religacao", 2.0),
            ("multa", 2.0),
            ("crefaz", 2.5),
            ("produto", 1.2),
            ("excluir cobranca", 2.5),
            ("retirar produto", 2.5),
            "exclusao de crefaz",
            "cancelar produto",
        ),
    ),
    "troca_titularidade": TaxonomyEntry(
        description="Erro relacionado a troca de titularidade (faturamento indevido)",
        category="cadastro",
        severity="medium",
        keywords=(
            ("troca de titularidade", 3.5),
            ("titularidade", 2.5),
            ("novo titular", 2.0),
            ("mudanca de titular", 2.5),
            "transferencia de titularidade",
        ),
    ),
    "endereco_tipologia": TaxonomyEntry(
        description="Endereco, tipologia ou unidade divergente / ordem em UC errada",
        category="cadastro",
        severity="medium",
        keywords=(
            ("endereco divergente", 3.0),
            ("tipologia incorreta", 3.0),
            ("tipologia errada", 3.0),
            ("outra area", 2.5),
            ("unidade errada", 2.5),
            ("instalacao errada", 2.5),
            ("nova ordem", 1.5),
            "mudou de endereco",
            "endereco errado",
        ),
    ),
    "data_vencimento_ciclo": TaxonomyEntry(
        description="Problemas de ciclo/vencimento (duas faturas no mes, data fixa)",
        category="ciclo_faturamento",
        severity="low",
        keywords=(
            ("duas faturas", 3.0),
            ("mesmo mes", 1.5),
            ("data de vencimento", 2.5),
            ("vencimento proximo", 2.5),
            ("vecto fixo", 2.5),
            ("ciclo de leitura", 2.5),
            "dt de leitura",
            "periodo de dias",
        ),
    ),
    "art_113_regulatorio": TaxonomyEntry(
        description="Aplicacoes de ART 113 / recuperacao de consumo regulatoria",
        category="regulatorio",
        severity="critical",
        keywords=(
            ("art 113", 4.0),
            ("art. 113", 4.0),
            ("artigo 113", 3.5),
            ("recuperacao de consumo", 3.0),
            ("cocel", 2.0),
            "prodist",
        ),
    ),
    "leitura_confirmada_improcedente": TaxonomyEntry(
        description="Leitura aferida ou confirmada — reclamacao improcedente",
        category="resolucao",
        severity="low",
        keywords=(
            ("leitura confirmada", 3.5),
            ("leitura conferida", 3.0),
            ("improcedente", 3.0),
            ("procedente parcial", 2.0),
            ("sem divergencia", 2.5),
            ("fatura correta", 2.5),
            "leitura aferida",
            "comprovada",
            "sem variacao",
        ),
        patterns=(
            r"\bimpro?cedent",
            r"\bleitura\s+confer[ií]d",
        ),
    ),
}


CANONICAL_LABEL_MAP: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("digitacao", ("digitacao", "digitação")),
    (
        "leitura_estimada_media",
        (
            "media",
            "média",
            "estimada",
            "faturamento_por_media",
            "faturamento_por_média",
            "plurimensal",
            "calculo_de_m",
            "cálculo_de_m",
            "aplicacao_de_media",
            "aplicação_de_média",
        ),
    ),
    ("medidor_danificado", ("medidor", "defeito", "danificado", "visor", "embacada", "aferida")),
    ("impedimento_acesso", ("acesso", "impedimento", "portao", "portão", "sem_acesso")),
    ("autoleitura_cliente", ("autoleitura", "foto", "video", "vídeo", "evidencia")),
    (
        "endereco_tipologia",
        ("endereco", "endereço", "tipologia", "outra_area", "outra_área", "localizacao", "localização"),
    ),
    (
        "refaturamento_corretivo",
        ("refatur", "fatura_corrigida", "ajuste_leitura", "ajuste_de_fatura", "nota_credito"),
    ),
    (
        "compensacao_gd",
        ("gd", "geracao_distribuida", "geração_distribuída", "injetada", "compensacao", "compensação"),
    ),
    ("cobranca_indevida", ("autoreligacao", "autoreligação", "multa", "crefaz", "cobranca_indevida")),
    ("troca_titularidade", ("titularidade", "titular")),
    ("data_vencimento_ciclo", ("duas_faturas", "vencimento", "vecto", "ciclo")),
    ("art_113_regulatorio", ("art_113", "art.113", "artigo_113", "recuperacao", "recuperação")),
    (
        "leitura_confirmada_improcedente",
        ("confirmada", "conferida", "improcedente", "sem_variacao", "sem_variação"),
    ),
    ("consumo_elevado_revisao", ("consumo_elevado", "variacao", "variação", "revisao", "revisão")),
)

# Retrocompatibilidade para callers antigos que importavam KEYWORD_TAXONOMY.
KEYWORD_TAXONOMY: dict[str, list[str]] = {
    label: [_kw if isinstance(_kw, str) else _kw[0] for _kw in entry.keywords]
    for label, entry in TAXONOMY.items()
}


CATEGORY_SEVERITY_WEIGHT = {"critical": 4.0, "high": 3.0, "medium": 2.0, "low": 1.0}


def normalize_text(text: str) -> str:
    """Casefold + strip accents + collapse whitespace. Determinista e idempotente."""
    if not text:
        return ""
    decomposed = unicodedata.normalize("NFD", text)
    stripped = "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")
    return re.sub(r"\s+", " ", stripped.casefold()).strip()


@dataclass(frozen=True, slots=True)
class ErroLeituraTrainingResult:
    macro_f1: float
    classes: tuple[str, ...]
    backend: str
    report: dict[str, Any]


class KeywordErroLeituraClassifier:
    """Classificador determinista baseado em taxonomia ponderada.

    Diferencas vs v1:
      - Pesos por termo (tuplas (termo, peso)) — termos muito caracteristicos pesam mais.
      - Regex patterns opcionais por classe (mais flexiveis que match literal).
      - Lista de `negatives` que zera o score de uma classe quando presentes.
      - Normalizacao unicode + acentos (crucial para SP, que escreve sem acentos).
      - Threshold adaptativo: se top-score < minimo absoluto E top/second < margem,
        retorna `indefinido` em vez de `outros` — permite isolar ambiguos.
    """

    def __init__(
        self,
        *,
        taxonomy: dict[str, TaxonomyEntry] | None = None,
        min_score: float = 1.0,
        margin_ratio: float = 1.05,
    ) -> None:
        self.taxonomy = taxonomy or TAXONOMY
        self.min_score = min_score
        self.margin_ratio = margin_ratio

    def score_text(self, text: str) -> dict[str, float]:
        normalized = normalize_text(text)
        if not normalized:
            return {label: 0.0 for label in self.taxonomy}
        scores: dict[str, float] = {}
        for label, entry in self.taxonomy.items():
            score = 0.0
            for term in entry.keywords:
                token, weight = (term, 1.0) if isinstance(term, str) else term
                token_norm = normalize_text(token)
                if token_norm and token_norm in normalized:
                    score += weight
            for pattern in entry.patterns:
                if re.search(pattern, normalized):
                    score += 2.0
            for negative in entry.negatives:
                if normalize_text(negative) in normalized:
                    score = 0.0
                    break
            scores[label] = score
        return scores

    def predict_proba(self, texts: list[str]) -> list[dict[str, float]]:
        results: list[dict[str, float]] = []
        for text in texts:
            scores = self.score_text(text)
            total = sum(scores.values())
            if total <= 0.0:
                # distribuicao uniforme -> top-score baixo, sera marcado como "indefinido".
                uniform = 1.0 / max(len(self.taxonomy), 1)
                results.append({label: uniform for label in self.taxonomy})
                continue
            results.append({label: value / total for label, value in scores.items()})
        return results

    def classify(self, text: str) -> dict[str, Any]:
        raw_scores = self.score_text(text)
        total = sum(raw_scores.values())
        probabilities = (
            {label: value / total for label, value in raw_scores.items()}
            if total > 0.0
            else {label: 1.0 / max(len(self.taxonomy), 1) for label in self.taxonomy}
        )
        ordered = sorted(raw_scores.items(), key=lambda item: item[1], reverse=True)
        top_label, top_score = ordered[0]
        second_score = ordered[1][1] if len(ordered) > 1 else 0.0

        is_weak = top_score < self.min_score
        is_ambiguous = second_score > 0 and top_score < second_score * self.margin_ratio
        if is_weak or is_ambiguous:
            predicted = "indefinido"
        else:
            predicted = top_label

        top3 = [
            {
                "classe": label,
                "probabilidade": round(probabilities[label], 4),
                "score_bruto": round(raw_scores[label], 2),
            }
            for label, _ in ordered[:3]
        ]
        return {
            "classe": predicted,
            "probabilidade": round(probabilities[top_label], 4),
            "score_bruto": round(top_score, 2),
            "top3": top3,
            "ambiguous": is_ambiguous,
            "weak_signal": is_weak,
        }


class ErroLeituraClassifierTrainer:
    """Trains a calibrated multiclass classifier over text embeddings."""

    def __init__(self, embedding_builder: TextEmbeddingBuilder | None = None) -> None:
        self.embedding_builder = embedding_builder or TextEmbeddingBuilder()
        self.keyword_classifier = KeywordErroLeituraClassifier()
        self.label_encoder = LabelEncoder()
        self.model: Any | None = None

    def weak_labels(self, frame: pd.DataFrame) -> pd.Series:
        labels = frame.get("causa_raiz", pd.Series(index=frame.index, dtype=object)).fillna("").astype(str)
        normalized = labels.str.strip().str.casefold().str.replace(r"\s+", "_", regex=True)
        inferred = pd.Series(
            [self.keyword_classifier.classify(text)["classe"] for text in frame["texto_completo"].fillna("")],
            index=frame.index,
        )
        canonical = normalized.map(canonical_label)
        missing = canonical.isna()
        canonical.loc[missing] = inferred.loc[missing]
        # fallback final: se ainda indefinido/NaN, usa a classe dominante do texto.
        canonical = canonical.fillna("indefinido").replace({"": "indefinido"})
        return canonical

    def train(self, frame: pd.DataFrame) -> ErroLeituraTrainingResult:
        if len(frame) < 4:
            raise ValueError("Sao necessarias pelo menos 4 linhas para treinar o classificador de erro leitura.")
        labels = self.weak_labels(frame)
        embeddings = self.embedding_builder.build(frame).frame
        feature_columns = [column for column in embeddings.columns if column.startswith("embedding_")]
        target = self.label_encoder.fit_transform(labels)
        base_model = LogisticRegression(max_iter=500, class_weight="balanced")
        min_class_count = int(pd.Series(target).value_counts().min())
        if min_class_count >= 2:
            self.model = CalibratedClassifierCV(base_model, method="sigmoid", cv=2)
        else:
            self.model = base_model
        self.model.fit(embeddings[feature_columns], target)

        macro_scores: list[float] = []
        splitter = TimeSeriesSplit(n_splits=min(3, max(2, len(frame) // 3)))
        for train_index, test_index in splitter.split(embeddings):
            pipeline = Pipeline([("model", LogisticRegression(max_iter=500, class_weight="balanced"))])
            pipeline.fit(embeddings.iloc[train_index][feature_columns], target[train_index])
            prediction = pipeline.predict(embeddings.iloc[test_index][feature_columns])
            macro_scores.append(float(f1_score(target[test_index], prediction, average="macro", zero_division=0)))

        fitted_predictions = self.model.predict(embeddings[feature_columns])
        report = classification_report(
            target,
            fitted_predictions,
            target_names=self.label_encoder.classes_,
            output_dict=True,
            zero_division=0,
        )
        return ErroLeituraTrainingResult(
            macro_f1=float(np.mean(macro_scores)) if macro_scores else 0.0,
            classes=tuple(self.label_encoder.classes_.tolist()),
            backend="logistic-regression-calibrated",
            report=report,
        )

    def classify(self, text: str) -> dict[str, Any]:
        if self.model is None:
            return self.keyword_classifier.classify(text)
        frame = pd.DataFrame({"ordem": ["ad_hoc"], "texto_completo": [text]})
        embeddings = self.embedding_builder.build(frame).frame
        feature_columns = [column for column in embeddings.columns if column.startswith("embedding_")]
        probabilities = self.model.predict_proba(embeddings[feature_columns])[0]
        top_indices = np.argsort(probabilities)[-3:][::-1]
        top3 = [
            {"classe": self.label_encoder.classes_[index], "probabilidade": round(float(probabilities[index]), 4)}
            for index in top_indices
        ]
        return {"classe": top3[0]["classe"], "probabilidade": top3[0]["probabilidade"], "top3": top3}


def canonical_label(value: object) -> str | None:
    """Mapeia label bruto (label de operador CE ou texto livre) para a taxonomia v2."""
    if value is None or pd.isna(value):
        return None
    text = str(value).strip().casefold()
    if not text or text == "nan":
        return None
    normalized = normalize_text(text).replace(" ", "_")
    for label, patterns in CANONICAL_LABEL_MAP:
        if any(pattern in normalized for pattern in patterns):
            return label
    if text in TAXONOMY:
        return text
    return None


def taxonomy_metadata() -> pd.DataFrame:
    """DataFrame com metadados (classe, categoria, severidade, descricao)."""
    rows = [
        {
            "classe": label,
            "categoria": entry.category,
            "severidade": entry.severity,
            "peso_severidade": CATEGORY_SEVERITY_WEIGHT.get(entry.severity, 1.0),
            "descricao": entry.description,
            "n_keywords": len(entry.keywords),
        }
        for label, entry in TAXONOMY.items()
    ]
    return pd.DataFrame(rows)
