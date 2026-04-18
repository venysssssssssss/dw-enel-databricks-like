# Visão Geral das Sprints

## Metodologia

- **Duração**: 2 semanas por sprint
- **Total**: 19 sprints (~38 semanas / 9-10 meses)
- **Cerimônias**: Planning (dia 1), Daily (diária), Review + Retro (último dia)

## Roadmap de Sprints

```
FASE 0 — DESCOBERTA
├── Sprint 01: Discovery & Project Setup

FASE 1 — FUNDAÇÃO
├── Sprint 02: Infraestrutura Core (MinIO, PostgreSQL, Nessie)
├── Sprint 03: Processing & Orchestration (Spark, Airflow, Trino)

FASE 2 — INGESTÃO & SILVER
├── Sprint 04: Bronze Layer — Ingestão de Fontes Prioritárias
├── Sprint 05: Silver Layer — Curadoria e Padronização
├── Sprint 06: Data Quality & Reconciliação

FASE 3 — GOLD & CONSUMO
├── Sprint 07: Gold Layer — Modelagem Dimensional (Fatos & Dimensões)
├── Sprint 08: BI — Superset Dashboards
├── Sprint 09: FastAPI — Exportação e Consulta

FASE 4 — ML & OPERAÇÃO ASSISTIDA
├── Sprint 10: Feature Engineering & ML Infrastructure
├── Sprint 11: Modelos Preditivos (Training & Validation)
├── Sprint 12: MLOps, Scoring Pipeline & Observabilidade Final

FASE 5 — EXPERIÊNCIA CONVERSACIONAL & RAG
├── Sprint 13: Erros de Leitura com IA
├── Sprint 14: UX de Excelência
├── Sprint 15: Chat RAG ENEL (baseline)
├── Sprint 16: React + Rust + Unified Data Plane
├── Sprint 17: RAG SP/CE Training
├── Sprint 18: RAG Semantic Intelligence
├── Sprint 19: RAG Performance, Contexto e Busca Semântica
```

## Dependências entre Sprints

```
Sprint 01 ──► Sprint 02 ──► Sprint 03
                               │
                    ┌──────────┤
                    ▼          ▼
              Sprint 04 ──► Sprint 05 ──► Sprint 06
                                              │
                                    ┌─────────┤
                                    ▼         ▼
                              Sprint 07 ──► Sprint 08
                                    │       Sprint 09
                                    ▼
                              Sprint 10 ──► Sprint 11 ──► Sprint 12
                                                       │
                                                       ▼
                              Sprint 13 ──► Sprint 14 ──► Sprint 15
                                                       │
                                                       ▼
                              Sprint 16 ──► Sprint 17 ──► Sprint 18 ──► Sprint 19
```

## Definition of Done (DoD) — Global

Cada item de sprint é considerado "Done" quando:
- [ ] Código implementado e revisado
- [ ] Testes passando (unitários + integração quando aplicável)
- [ ] Documentação atualizada
- [ ] Pipeline executa end-to-end sem erros
- [ ] Dados conferidos por amostragem
- [ ] Commit no repositório Git

## Métricas de Acompanhamento

| Métrica | Medição | Target |
|---|---|---|
| Velocity | Story points entregues por sprint | Estabilizar após Sprint 3 |
| Pipeline uptime | % de DAGs sem falha | ≥ 95% |
| Cobertura de testes | Linhas cobertas por testes | ≥ 80% (serviços), ≥ 60% (pipelines) |
| Data quality pass rate | % de testes GE passando | ≥ 98% |
| Bugs em produção | Bugs encontrados pós-deploy | ≤ 2 por sprint |
