"""Known RAG question seeds derived from observed chat telemetry.

The seed list intentionally stores variants, not generated answers. Answers are
resolved from current data cards at runtime so they stay tied to dataset_hash.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

KnownRegion = Literal["CE", "SP", "CE+SP"] | None

SEED_VERSION = "2026-04-19.1"


@dataclass(frozen=True, slots=True)
class KnownQuestionSeed:
    seed_id: str
    variants: tuple[str, ...]
    intent: str
    region: KnownRegion
    anchors: tuple[str, ...]
    answer_mode: str = "card_summary"
    min_score: float = 0.92


KNOWN_QUESTION_SEEDS: tuple[KnownQuestionSeed, ...] = (
    KnownQuestionSeed(
        "ce-total-overview",
        (
            "Quantas ordens existem em CE?",
            "Qual o total de reclamações de CE no dataset?",
            "No CE, qual a visão geral operacional?",
            "Qual o maior motivo de reclamação nos dados totais de CE?",
            "Qual o volume total de reclamações no Ceará?",
            "Resumo operacional de CE",
            "Quantas reclamações totais existem no Ceará?",
        ),
        "analise_dados",
        "CE",
        ("ce-reclamacoes-totais-overview",),
    ),
    KnownQuestionSeed(
        "ce-main-subjects",
        (
            "Qual o principal assunto em CE?",
            "Quais são os top 3 assuntos de CE?",
            "No CE, qual percentual do principal assunto?",
            "Quais são os principais motivos em CE?",
            "Quais são os principais assuntos de reclamação em CE?",
            "Ranking de assuntos no Ceará",
            "Top 5 assuntos de reclamação em CE",
        ),
        "analise_dados",
        "CE",
        ("ce-reclamacoes-totais-assuntos",),
    ),
    KnownQuestionSeed(
        "ce-main-causes",
        (
            "Quais são as principais causas em CE?",
            "Qual a causa canônica mais frequente no CE?",
            "No CE, quais causas têm maior volume?",
            "Qual o número de causas rotuladas em CE?",
            "Qual taxa de causa rotulada no CE?",
            "Quais causas lideram no Ceará?",
            "Top causas canônicas em CE",
        ),
        "analise_dados",
        "CE",
        ("ce-reclamacoes-totais-causas", "top-causas-raiz"),
    ),
    KnownQuestionSeed(
        "ce-refaturamento",
        (
            "Qual a taxa de refaturamento em CE?",
            "A taxa de refaturamento de CE está acima de 10%?",
            "Quantas ordens refaturadas existem em CE?",
            "Qual a taxa de refaturamento resolvido de CE?",
            "Como está o refaturamento por assunto em CE?",
            "Dentro de CE, em quais assuntos o refaturamento aparece com mais frequência?",
            "Volume de refaturamento no Ceará",
        ),
        "analise_dados",
        "CE",
        ("ce-reclamacoes-totais-refaturamento",),
    ),
    KnownQuestionSeed(
        "ce-refaturamento-produtos",
        (
            "O que é REFATURAMENTO PRODUTOS em CE?",
            "Por que REFATURAMENTO PRODUTOS é recorrente em CE?",
            "Explique REFATURAMENTO PRODUTOS e traga os principais drivers em CE",
            "No universo total de CE, quais causas lideram dentro de REFATURAMENTO PRODUTOS?",
            "O que seria REFATURAMENTO PRODUTOS ? Por que isso é um motivo de reclamação recorrente?",
            "Qual medida prática posso adotar para reduzir reclamações de refaturamento em CE?",
            "Drivers de REFATURAMENTO PRODUTOS no Ceará",
        ),
        "analise_dados",
        "CE",
        (
            "ce-reclamacoes-totais-assuntos",
            "ce-reclamacoes-totais-refaturamento",
            "ce-reclamacoes-totais-assunto-causa",
            "playbook-acoes-cliente",
        ),
    ),
    KnownQuestionSeed(
        "ce-monthly",
        (
            "Mostre a evolução mensal em CE.",
            "Em CE, qual mês teve pico de ordens?",
            "Em CE, a base cobre quantos dias?",
            "Qual a cobertura temporal de CE?",
            "Como foi a evolução temporal no Ceará?",
            "Qual mês concentrou mais reclamações em CE?",
            "Série mensal de reclamações em CE",
        ),
        "analise_dados",
        "CE",
        ("ce-reclamacoes-totais-evolucao", "ce-reclamacoes-totais-mensal-assuntos"),
    ),
    KnownQuestionSeed(
        "ce-group-quality",
        (
            "Em CE, qual grupo tarifário é mais frequente?",
            "Qual a distribuição por grupo no CE?",
            "No CE, qual o resumo de qualidade dos dados?",
            "Quais caveats devo considerar em CE?",
            "Como está a qualidade da base de CE?",
            "Qual grupo lidera no Ceará?",
            "Caveats da base do Ceará",
        ),
        "analise_dados",
        "CE",
        ("ce-reclamacoes-totais-grupo", "data-quality-notes"),
    ),
    KnownQuestionSeed(
        "sp-overview",
        (
            "Quantas ordens existem em SP?",
            "Qual o total de reclamações de SP no dataset?",
            "Qual o resumo de qualidade dos dados em SP?",
            "SP tem refaturamento resolvido igual a zero?",
            "SP tem predominância de erro de leitura?",
            "Resumo operacional de SP",
            "Quantos tickets existem em São Paulo?",
        ),
        "analise_dados",
        "SP",
        ("sp-n1-overview", "data-quality-notes"),
    ),
    KnownQuestionSeed(
        "sp-subjects-causes",
        (
            "Qual o principal assunto em SP?",
            "Quais são as principais causas em SP?",
            "Qual o número de causas rotuladas em SP?",
            "Qual motivo consolidado lidera em SP?",
            "Quais assuntos lideram em São Paulo?",
            "Quais causas lideram em São Paulo?",
            "Top assuntos e causas em SP",
        ),
        "analise_dados",
        "SP",
        ("sp-n1-assuntos", "sp-n1-causas", "data-quality-notes"),
    ),
    KnownQuestionSeed(
        "sp-refaturamento",
        (
            "Qual a taxa de refaturamento em SP?",
            "Quantas ordens refaturadas existem em SP?",
            "SP tem refaturamento resolvido igual a zero?",
            "Como está o refaturamento em SP?",
            "Existe refaturamento resolvido em SP?",
            "Taxa de refaturamento de São Paulo",
            "Por que SP mostra refaturamento zero?",
        ),
        "analise_dados",
        "SP",
        ("sp-n1-overview", "data-quality-notes"),
    ),
    KnownQuestionSeed(
        "sp-monthly-group",
        (
            "Mostre a evolução mensal em SP.",
            "Em SP, qual mês teve pico de ordens?",
            "Qual a cobertura temporal de SP?",
            "Em SP, qual grupo tarifário é mais frequente?",
            "Qual grupo tarifário lidera em SP?",
            "Como evoluíram os tickets de SP por mês?",
            "Cobertura temporal de São Paulo",
        ),
        "analise_dados",
        "SP",
        ("sp-n1-mensal", "sp-n1-grupo", "data-quality-notes"),
    ),
    KnownQuestionSeed(
        "sp-meter-types",
        (
            "Quais os tipos de medidores existentes em SP ?",
            "Quais são os TIPOS dos medidores existentes nas instalações de SP ?",
            "Qual tipo de medidor que mais dá problema em SP",
            "Dos medidores existentes em SP, quais mais geram reclamações ?",
            "Quais tipos de medidores aparecem nas reclamações de SP?",
            "Ranking de tipos de medidor em São Paulo",
            "Medidor mais recorrente em reclamações SP",
        ),
        "analise_dados",
        "SP",
        ("sp-tipos-medidor", "sp-n1-top-instalacoes", "data-quality-notes"),
    ),
    KnownQuestionSeed(
        "sp-meter-reasons",
        (
            "Quais são os top 5 motivos para medidor digital em SP?",
            "Dessas reclamações de SP, quais são os top 5 motivos para o medidor digital?",
            "Dessas reclamações geradas, quais são os top 5 motivos de reclamações para o medidor digital em SP?",
            "Quais são os motivos mais recorrentes para medidores digitais em SP e o volume de cada um?",
            "No medidor analógico em SP, quais são as principais causas de reclamação?",
            "Top motivos do medidor ciclométrico em SP",
            "Entre os tipos de medidor em SP, quais motivos aparecem com maior frequência?",
            "Após ver os motivos do medidor digital, qual ação recomendada para SP?",
            "Motivos por tipo de medidor em SP",
        ),
        "analise_dados",
        "SP",
        ("sp-causas-por-tipo-medidor", "sp-tipos-medidor", "playbook-acoes-cliente"),
    ),
    KnownQuestionSeed(
        "sp-digitacao",
        (
            "Qual percentual de digitacao no medidor digital em SP?",
            "Quais tipos de medidores são os mais recorrentes em reclamações que envolvem digitação?",
            "Quais instalações concentram digitação e quais tipos de medidor estão associados?",
            "Quais instalações mais tem problemas com erros de digitação ?",
            "Tipos de medidor em casos de digitação em SP",
            "Instalações com maior volume de digitação",
            "Erro de digitação por tipo de medidor em SP",
        ),
        "analise_dados",
        "SP",
        ("sp-tipos-medidor-digitacao", "instalacoes-digitacao", "sp-causas-por-tipo-medidor"),
    ),
    KnownQuestionSeed(
        "ce-sp-volume",
        (
            "Compare CE e SP em volume total.",
            "Qual regional tem maior volume, CE ou SP?",
            "Qual a participação de CE no total CE+SP?",
            "Qual a participação de SP no total CE+SP?",
            "CE tem mais ordens que SP?",
            "Resumo comparativo CE e SP com caveats.",
            "Quem tem mais reclamações, CE ou SP?",
        ),
        "analise_dados",
        "CE+SP",
        ("visao-geral", "regiao-ce", "regiao-sp", "data-quality-notes"),
    ),
    KnownQuestionSeed(
        "ce-sp-refaturamento",
        (
            "Compare CE e SP na taxa de refaturamento.",
            "Qual regional tem maior taxa de refaturamento, CE ou SP?",
            "Quais reclamações possuem maior taxa de refaturamento?",
            "Compare CE e SP para priorização: principais motivos consolidados e risco operacional",
            "Refaturamento CE versus SP",
            "Onde priorizar refaturamento entre CE e SP?",
        ),
        "analise_dados",
        "CE+SP",
        ("ce-vs-sp-refaturamento", "refaturamento", "data-quality-notes"),
    ),
    KnownQuestionSeed(
        "ce-sp-causes-taxonomy",
        (
            "Quais diferenças de causa entre CE e SP?",
            "Qual a causa-raiz mais frequente?",
            "Qual a taxonomia consolidada de motivos em CE e SP?",
            "Mostre combinações de assunto e causa mais frequentes no CE+SP",
            "No contexto CE+SP, relacione assunto e causa para priorização operacional",
            "CE e SP têm o mesmo perfil de assunto?",
        ),
        "analise_dados",
        "CE+SP",
        ("motivos-taxonomia-ce-sp", "ce-vs-sp-causas", "top-assuntos", "top-causas-raiz"),
    ),
    KnownQuestionSeed(
        "ce-sp-monthly-group",
        (
            "Mostre CE versus SP na evolução mensal.",
            "Compare CE e SP em cobertura temporal.",
            "Compare CE/SP por grupo tarifário.",
            "Qual a evolução mensal comparada entre CE e SP?",
            "Qual regional tem pico mensal maior?",
            "Como comparar grupo tarifário entre CE e SP?",
        ),
        "analise_dados",
        "CE+SP",
        ("ce-vs-sp-mensal", "grupo-tarifario", "data-quality-notes"),
    ),
    KnownQuestionSeed(
        "glossary-business",
        (
            "O que é ACF/ASF?",
            "O que é ACF ?",
            "O que é ASF",
            "Como é calculado o flag ACF/ASF?",
            "O que é esse projeto",
            "O que é energia",
        ),
        "glossario",
        None,
        ("business-glossary", "regra-acf", "regra-asf"),
    ),
    KnownQuestionSeed(
        "dashboard-sprint-dev",
        (
            "qual a sprint 13?",
            "Quais os KPIs da Sprint 13?",
            "Como interpretar o gráfico de radar por grupo?",
            "Como rodar o pipeline Bronze → Silver localmente?",
            "Como funciona a ingestão na camada Bronze?",
            "Como o modelo de erro de leitura classifica os casos?",
        ),
        "sprint",
        None,
        ("sprint-13", "radar-causas", "bronze-silver", "erro-leitura-modelo"),
    ),
    KnownQuestionSeed(
        "regional-refusal",
        (
            "Quantas ordens existem no Rio de Janeiro?",
            "E no Rio de Janeiro?",
            "Qual a taxa de refaturamento em Minas Gerais?",
            "Mostre os dados da Bahia.",
            "Quais números de Pernambuco?",
            "Quero o comparativo nacional de todas as regionais.",
            "Existe base para responder top motivos por tipo de medidor em RJ?",
        ),
        "out_of_regional_scope",
        None,
        (),
        "regional_refusal",
        1.0,
    ),
    KnownQuestionSeed(
        "domain-refusal",
        (
            "Qual foi o campeão brasileiro de 2012?",
            "Me passe uma receita de bolo de cenoura.",
            "Explique programação orientada a objetos em Python.",
            "Qual é a previsão do tempo para amanhã?",
            "Como funciona a bolsa de valores nos EUA?",
            "teste",
        ),
        "out_of_scope",
        None,
        (),
        "domain_refusal",
        0.94,
    ),
)


def known_variant_count() -> int:
    return sum(len(seed.variants) for seed in KNOWN_QUESTION_SEEDS)
