# Sprint 24 — Web Severidade ENEL

## 1. Título

Sprint 24 — Web Severidade ENEL: experiência executiva para reclamações Alta e Crítica.

## 2. Objetivo macro

Transformar a camada Web React em uma experiência executiva, institucional e confiável para apresentar reclamações por severidade dentro da ENEL, com foco em volume, categorias, causas canônicas, procedência/improcedência, reincidência por instalação e impacto financeiro.

Preservar a arquitetura atual do repositório: React + Vite + TypeScript + TanStack Router + TanStack Query + FastAPI/data-plane.

## 3. Diagnóstico do estado atual do repo

### Existente

- `apps/web/src/main.tsx` centraliza rotas TanStack Router.
- `apps/web/src/components/shared/Shell.tsx` seleciona `data-surface="aconchegante"` para rotas BI.
- `apps/web/src/components/shared/Sidebar.tsx` organiza navegação principal.
- `apps/web/src/components/bi/` contém padrões reutilizáveis como `Hero`, `KpiStrip`, `StoryBlock`, `Charts` e componentes específicos de severidade.
- `apps/web/src/hooks/useAggregation.ts` consome `/v1/aggregations/{view_id}` via TanStack Query.
- `src/data_plane/views.py` mantém `VIEW_REGISTRY` com contratos declarativos para agregações.
- `src/data_plane/store.py` aplica filtros, carrega silver e executa views.
- `src/api/routers/dashboard.py` expõe `/v1/aggregations/{view_id}` com ETag e cache em memória.
- `src/viz/erro_leitura_dashboard_data.py` prepara frame analítico e já contém base para severidade derivada da taxonomia.
- Referências visuais existem em `apps/web/references/`, incluindo `MIS BI Aconchegante.html`, `Refactor.html` e referência específica de severidade.

### Novo ou a consolidar

- Rotas executivas de severidade Alta e Crítica devem permanecer explícitas na navegação.
- Contratos de severidade precisam ser estáveis, pequenos e documentados.
- Páginas devem usar template único para evitar duplicação entre Alta e Crítica.
- Estados loading, empty e error precisam ser profissionais por bloco.
- Testes backend e smoke frontend precisam cobrir as novas rotas/views.

## 4. Problema de negócio

A diretoria, coordenação e operação precisam entender rapidamente onde estão os casos mais relevantes de reclamações por severidade. A camada Web deve responder:

- Qual é o volume de reclamações Alta e Crítica?
- Quais categorias concentram o problema?
- Quais causas canônicas explicam o volume?
- Quanto é procedente ou improcedente?
- Quais instalações reincidem?
- Qual é o impacto financeiro médio nas ocorrências procedentes?
- Onde agir primeiro?

Sem essa leitura executiva, a aplicação parece exploração técnica, não produto analítico corporativo.

## 5. Resultado esperado

Ao final da sprint, a Web deve entregar:

- Página executiva existente preservada.
- Página de Severidade Alta funcional.
- Página de Severidade Crítica funcional.
- KPIs, gráficos, tabela do assistente e ranking consumindo agregações reais.
- Navegação clara no Shell/Sidebar/Topbar.
- Visual maduro, institucional e coerente com tokens ENEL/aconchegante/graphite.
- Contratos de API documentados.
- Testes unitários backend e smoke/e2e frontend.

## 6. Escopo

- Criar ou consolidar rotas:
  - `/bi/severidade-alta`
  - `/bi/severidade-critica`
- Consolidar template React único parametrizado por severidade.
- Evoluir componentes BI reutilizáveis de severidade.
- Criar/agregar views backend no data-plane para KPIs, série mensal, categorias, causas, achados do assistente e ranking.
- Tipar contratos TypeScript.
- Adicionar estados loading, empty e error.
- Documentar contratos e comandos de validação.

## 7. Fora de escopo

- Trocar Vite, React, TanStack Router ou TanStack Query.
- Criar backend fora de `/v1/aggregations/{view_id}`.
- Expor PII ou texto bruto sensível no frontend.
- Criar brand book ENEL externo ao repo.
- Generalizar para todas as regiões.
- Reescrever toda a experiência BI existente.

## 8. Arquitetura alvo

### Frontend

- `main.tsx` registra rotas.
- `Shell.tsx` aplica surface visual.
- `Sidebar.tsx` expõe navegação por severidade.
- `bi.severidade.tsx` orquestra dados e passa props para componentes.
- Componentes BI são puros, tipados e reutilizáveis.
- `useAggregation` continua sendo o ponto único de busca.

### Backend/data-plane

- `src/viz/erro_leitura_dashboard_data.py` concentra agregações pandas.
- `src/data_plane/views.py` registra views no `VIEW_REGISTRY`.
- `DataStore.aggregate_records()` mantém contrato com API.
- `/v1/aggregations/{view_id}` mantém cache, ETag e resposta `{view_id,dataset_hash,filters,data}`.

### Regra de negócio

- Severidade é derivada de `taxonomy_metadata()` por `causa_canonica`.
- Alta usa chave `high`.
- Crítica usa chave `critical`.
- Procedência usa o melhor proxy disponível hoje: `flag_resolvido_com_refaturamento`. Se campo de procedência explícito for criado no futuro, trocar no data-plane, não no frontend.

## 9. Rotas e navegação

- `Severidade Alta`: `/bi/severidade-alta`
- `Severidade Crítica`: `/bi/severidade-critica`
- Sidebar deve manter seção `Severidade` com:
  - MIS Executivo
  - Severidade Alta
  - Severidade Crítica
- Topbar deve mostrar:
  - `Severidade / Alta · SP`
  - `Severidade / Crítica · SP`
- Shell deve renderizar ambas com `data-surface="aconchegante"`.

## 10. Design system e UI/UX

### Existente a reaproveitar

- Tokens `brand`, `graphite`, `aconchegante`, `status` em `apps/web/src/lib/tokens.ts`.
- CSS da superfície aconchegante em `apps/web/src/styles.css`.
- Referências:
  - `apps/web/references/MIS BI Aconchegante.html`
  - `apps/web/references/MIS Aconchegante data.js`
  - `apps/web/references/MIS Aconchegante charts.js`
  - `apps/web/references/Refactor.html`
  - `apps/web/references/ENEL Severidade.html`

### Diretrizes

- Alta: atenção operacional com âmbar/terra, sem alarme excessivo.
- Crítica: prioridade institucional com plum/wine/status crit, sem poluição visual.
- Cores sempre têm função semântica.
- Cada página conta a história: volume → distribuição → causa → reincidência → impacto → ação.
- Gráficos devem priorizar leitura executiva, não exploração técnica crua.
- Tooltips devem explicar volume, percentual, procedência, reincidência e valor.
- Tabelas devem parecer ranking executivo, não dump bruto.
- Responsividade mínima: notebook 1366px, desktop 1440px, tela grande 1920px.

## 11. Contratos de dados/API

### Views obrigatórias

- `sp_severidade_alta_overview`
- `sp_severidade_critica_overview`
- `sp_severidade_alta_mensal`
- `sp_severidade_critica_mensal`
- `sp_severidade_alta_categorias`
- `sp_severidade_critica_categorias`
- `sp_severidade_alta_causas`
- `sp_severidade_critica_causas`
- `sp_severidade_alta_assistant_findings`
- `sp_severidade_critica_assistant_findings`
- `sp_severidade_alta_ranking`
- `sp_severidade_critica_ranking`

### KPI

- `severity`
- `total_reclamacoes`
- `categorias_identificadas`
- `procedentes_qtd`
- `procedentes_pct`
- `improcedentes_qtd`
- `improcedentes_pct`
- `reincidentes_qtd`
- `valor_medio_fatura_procedente`

### Mensal

- `ano_mes`
- `severity`
- `qtd_reclamacoes`

### Categorias

- `categoria`
- `qtd_reclamacoes`
- `percentual`

### Dispersão de causas canônicas

- `causa_canonica`
- `categoria`
- `qtd_reclamacoes`
- `percentual`
- `procedencia_pct`
- `reincidencia_qtd`
- `valor_medio_fatura`
- `severidade`

### Tabela do assistente

- `id`
- `severidade`
- `descricao_identificada`
- `categoria`
- `causa_canonica`
- `evidencia`
- `recomendacao_operacional`
- `confianca`

### Ranking reincidência

- `instalacao`
- `qtd_reincidencias`
- `categoria_top`
- `causa_canonica_top`
- `procedentes_qtd`
- `improcedentes_qtd`
- `valor_medio_fatura`
- `prioridade`

## 12. Componentes frontend a criar/refatorar

### Criar ou consolidar

- `SeverityPageHeader`
- `SeverityKpiStrip`
- `HorizontalCategoryBars`
- `CanonicalCauseScatter`
- `AssistantFindingsTable`
- `ReincidentInstallationsRanking`
- `EmptyState`
- `ChartTooltip`

### Refatorar

- `bi.severidade.tsx` deve ser o orquestrador de dados e narrativa.
- `SeverityCharts.tsx` deve manter componentes de gráfico coesos e sem regra de negócio pesada.
- `KpiStrip`, `Hero` e `StoryBlock` devem ser reaproveitados quando não comprometerem contrato específico da página.

## 13. Views backend/data-plane a criar/refatorar

### Reaproveitar

- `_attach_severidade`
- `_filter_sp_severidade`
- `sp_severidade_overview`
- `sp_severidade_mensal`
- `sp_severidade_categorias`
- `sp_severidade_causas`
- `sp_severidade_ranking`

### Criar

- `sp_severidade_assistant_findings`

### Ajustar

- Overview deve retornar nomes executivos do contrato.
- Mensal deve retornar `ano_mes`.
- Categorias deve ordenar desc e agrupar top N quando necessário.
- Causas deve retornar percentual, procedência, reincidência e valor médio.
- Ranking deve calcular prioridade com base em reincidência, procedência e valor médio.
- Payloads devem ser pequenos e adequados para dashboard.

## 14. Plano de execução por fases

### Fase 0 — Discovery técnico e inventário

- Confirmar estado git.
- Ler rotas, componentes BI, tokens, CSS, references, views, store e API.
- Inventariar contratos atuais.
- Confirmar campos reais disponíveis no frame preparado.
- Registrar gaps entre mock visual e dados reais.

### Fase 1 — Contratos de dados e views backend

- Padronizar views existentes.
- Criar views de achados do assistente.
- Registrar views no `VIEW_REGISTRY`.
- Preservar cache e ETag.
- Adicionar testes unitários.

### Fase 2 — Design system e componentes reutilizáveis

- Consolidar tokens e classes de severidade.
- Criar componentes reutilizáveis.
- Padronizar estados loading/empty/error.
- Padronizar tooltip e formatadores pt-BR.

### Fase 3 — Página Severidade Alta

- Ligar views `sp_severidade_alta_*`.
- Ajustar narrativa e microcopy de Alta.
- Validar KPIs, gráficos, findings e ranking.

### Fase 4 — Página Severidade Crítica

- Ligar views `sp_severidade_critica_*`.
- Ajustar narrativa de baixo volume e alto impacto.
- Validar prioridade e leitura institucional.

### Fase 5 — Polimento executivo, responsividade e acessibilidade

- Verificar labels, contraste e grids.
- Ajustar notebook/desktop/tela grande.
- Adicionar aria-labels e textos acessíveis.
- Revisar regressão visual nas rotas BI atuais.

### Fase 6 — Testes, hardening e documentação

- Rodar testes backend focados.
- Rodar testes frontend.
- Rodar build.
- Rodar smoke/e2e.
- Atualizar documentação final.

## 15. Tasks técnicas detalhadas com checklist

### Backend

- [ ] Validar severidade derivada de `taxonomy_metadata`.
- [ ] Criar fixtures para Alta e Crítica.
- [ ] Testar filtro SP + severidade.
- [ ] Ajustar contratos finais.
- [ ] Criar assistant findings.
- [ ] Adicionar prioridade no ranking.
- [ ] Registrar novas views.
- [ ] Testar vazio, dados reais mínimos e ordenação.

### Frontend

- [ ] Criar tipos TypeScript dos contratos.
- [ ] Centralizar configuração de severidade.
- [ ] Reusar template único.
- [ ] Criar componentes BI de severidade.
- [ ] Adicionar loading/error/empty.
- [ ] Garantir pt-BR para número, percentual e moeda.
- [ ] Validar navegação Sidebar/Topbar.
- [ ] Evitar duplicação Alta/Crítica.

### Testes/docs

- [ ] Atualizar testes unitários Python.
- [ ] Atualizar smoke Playwright.
- [ ] Rodar build Web.
- [ ] Documentar contratos.
- [ ] Registrar riscos residuais.

## 16. Critérios de aceite por fase

### Fase 0

- Inventário concluído sem inventar campos.
- Existing vs novo documentado.

### Fase 1

- Views retornam payloads estáveis.
- Testes unitários cobrem contratos.

### Fase 2

- Componentes reutilizáveis criados.
- Estados loading/empty/error padronizados.

### Fase 3

- Alta renderiza todos os blocos com agregações reais.

### Fase 4

- Crítica renderiza todos os blocos com agregações reais.

### Fase 5

- Não há sobreposição evidente de labels.
- Rotas BI atuais continuam utilizáveis.

### Fase 6

- Build passa.
- Testes focados passam.
- Smoke/e2e cobre navegação das novas páginas.

## 17. Testes e validações

- Unit backend para agregações em `src/viz/erro_leitura_dashboard_data.py`.
- Unit backend para registros em `src/data_plane/views.py`.
- API unit para `/v1/aggregations/{view_id}`.
- Vitest para helpers/adaptadores frontend, se criados.
- Playwright para navegação em `/bi/severidade-alta` e `/bi/severidade-critica`.
- Build frontend completo.

## 18. Riscos e mitigações

- Risco: procedência real não existir como campo explícito.
  - Mitigação: usar `flag_resolvido_com_refaturamento` como proxy documentado.
- Risco: texto bruto conter PII.
  - Mitigação: não expor `texto_completo`; findings usam agregados seguros.
- Risco: duplicação entre páginas.
  - Mitigação: template único parametrizado.
- Risco: visual virar cópia cega dos HTMLs de referência.
  - Mitigação: absorver padrões, não copiar estrutura sem contrato real.
- Risco: mudanças não commitadas confundirem autoria.
  - Mitigação: revisar status/diff antes de cada commit.

## 19. Definition of Done

- Rotas de Alta e Crítica acessíveis pela Sidebar.
- Página MIS existente preservada.
- KPIs carregam dados reais de agregação.
- Gráficos são legíveis e responsivos.
- Tabela do assistente filtra severidade.
- Ranking Top 10 filtra severidade.
- Contratos documentados.
- Testes backend adicionados.
- Smoke/e2e cobre navegação.
- Build Web passa.
- Sem duplicação grosseira entre páginas.

## 20. Comandos sugeridos de validação

```bash
rtk git status
rtk pytest tests/unit/viz/test_erro_leitura_dashboard_data.py tests/unit/test_data_plane_views.py tests/unit/test_data_plane_api.py
rtk run pnpm --dir apps/web test
rtk run pnpm --dir apps/web build
rtk run pnpm --dir apps/web test:e2e
rtk git diff --stat
```

## Resumo para execução por agente

- Ler arquivos primeiro.
- Alterar menor superfície possível.
- Preservar contratos existentes.
- Criar componentes reutilizáveis.
- Validar com build/test/e2e.
- Não inventar campo ou schema sem verificar no repo.
- Preservar `/v1/aggregations/{view_id}` e cache/ETag.
- Separar claramente existente de novo.
