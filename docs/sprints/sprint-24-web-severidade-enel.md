# Sprint 24 — Web Severidade ENEL (Alta / Crítica · SP)

**Executor principal**: Claude Opus 4.7
**Modo esperado**: reasoning `high` para arquitetura, `medium` para implementação
**Período sugerido**: 2 semanas (9 dias úteis com buffer)
**Precedência**: Sprint 23 (migração Streamlit → React), Sprint 17 (RAG · taxonomy v2), Sprint 21 (MIS Executivo)
**Status alvo**: `IN_PROGRESS`
**Estratégia de cutover**: incremental atrás da feature flag `severidade_v1`, coexistindo com a navegação do Sprint 23 até o aceite final do PO

---

## 1. Objetivo macro

Entregar duas telas analíticas de produto — **Severidade Alta** e **Severidade Crítica** — focadas no recorte **SP**, com paridade visual ao referencial `apps/web/references/ENEL Severidade.html`, alimentadas exclusivamente por **dados reais** do silver layer via data plane (`/v1/aggregations/...`). Sem mock, sem regra de negócio replicada no front.

A sprint não entrega "mais um dashboard". Ela introduz um **eixo analítico transversal de produto** — severidade taxonômica — que evoluirá para CE no Sprint 25 e para o conjunto Sudeste/Nordeste a seguir. Toda decisão arquitetural deve resistir a esse roadmap sem refactor.

Resultados objetivos da sprint:

- 2 rotas React em produção atrás de flag (`/bi/severidade-alta`, `/bi/severidade-critica`);
- 5 famílias de view (10 ViewSpecs) registradas no `VIEW_REGISTRY` do data plane;
- p95 de TTFB do JSON ≤ 250 ms com cache memória 60 s;
- Lighthouse desktop Performance ≥ 95, mobile-mid ≥ 85, A11y ≥ 90;
- 100% dos KPIs e gráficos derivados de aggregation endpoints versionados por `dataset_hash`;
- Cobertura E2E mínima: navegação entre rotas, cross-filter categoria → causa → ranking, tooltip, atalhos `2`/`3`.

---

## 2. Contexto real do repositório

### 2.1 Estado herdado do Sprint 23

A migração Streamlit → React entregou:

- Tanstack Router com lazy-route splitting (`apps/web/src/main.tsx`);
- contrato de filtros e store Zustand (`apps/web/src/state/filters-store.ts`);
- ETag + `If-None-Match` no cliente (`apps/web/src/lib/api.ts`);
- versionamento por `dataset_hash` (`/v1/dataset/version`);
- shell aconchegante e graphite com `data-surface` (`apps/web/src/components/shared/Shell.tsx`);
- componentes BI base (Hero, KpiStrip, StoryBlock, Charts via Recharts).

Todas essas peças permanecem **sem modificações invasivas** no Sprint 24. A sprint apenas estende.

### 2.2 Backend disponível e o que falta

`src/data_plane/views.py` registra `severity_heatmap`, `mis_executive_summary`, `mis_monthly_mis`, `category_breakdown`, `top_instalacoes_por_regional`. Esses **não atendem** o desenho da página de severidade — recortam por região, não por severidade × região × procedência × reincidência simultaneamente.

A sprint adiciona uma família dedicada `sp_severidade_*` em vez de inflar as views existentes com novos kwargs. Justificativa SOLID: cada view tem 1 responsabilidade observacional, e o registro `ViewSpec(handler, kwargs={...})` é o ponto canônico para parametrizar `severidade in {high, critical}`.

### 2.3 Limitações conhecidas e dívidas pré-existentes

- `flag_resolvido_com_refaturamento` em SP fica `False` no silver atual. KPIs `procedentes / improcedentes / pct_procedentes` virão zerados. **Não é defeito do Sprint 24** — é dívida das ingestões SP. Mantemos os campos no contrato; quando o silver popular, a UI já refletirá sem mudança de código.
- Silver SP não traz `municipio` granular. Fallback "SP/SP" no `cidade` do ranking até Sprint 27 (enrichment de UC).
- O reference HTML mostra "descrições identificadas pelo assistente" como mock. Mantemos esse painel **fora do Sprint 24** (vai para Sprint 26 com RAG estruturado por ordem).

### 2.4 Source-of-truth de severidade

`src/ml/models/erro_leitura_classifier.py::taxonomy_metadata()` é a fonte canônica do mapeamento `causa_canonica → severidade ∈ {critical, high, medium, low}` com `peso_severidade`. **Toda lógica de severidade na sprint deve passar por esse helper** — nunca por strings literais espalhadas.

---

## 3. Não-objetivos (escopo barrado)

Para evitar escopo elástico:

- **Sem CE neste sprint.** Severidade CE é Sprint 25 (mesmas views com filtro `regiao=CE`).
- **Sem novas tabelas Iceberg / migration dbt.** Tudo deriva do silver atual + `taxonomy_metadata()`.
- **Sem agente IA por linha.** A coluna "descrições identificadas pelo assistente" do reference HTML não entra. Sprint 26.
- **Sem refactor do MIS Executivo existente** (`/bi/mis`). Apenas adiciona-se o link de nav.
- **Sem novo design system.** Reutiliza-se `aconchegante` surface, com extensão `sev-*` controlada por `[data-sev]`.
- **Sem reescrita do Recharts**. Os SVGs novos são complementares, não substitutos.

---

## 4. Frentes de trabalho — item a item

Cada frente: **motivação · entradas · saídas · contratos · riscos · validação · DoD**.

### Frente A — Backend: família `sp_severidade_*`

**Motivação.** O front precisa de 5 endpoints idempotentes, cacheáveis, com mesmo contrato `AggregationResponse<T>` (`view_id`, `dataset_hash`, `filters`, `data: T[]`). O cache é por `(view_id, dataset_hash, filters)` no `MemoryResponseCache` existente em `dashboard.py`.

**Arquivos de entrada.**

- `src/viz/erro_leitura_dashboard_data.py` — handlers + helpers de severidade.
- `src/data_plane/views.py` — registro `VIEW_REGISTRY`.
- `src/data_plane/store.py` — pipeline de filtros (`_apply_filters` já cobre 6 campos do contrato).
- `src/ml/models/erro_leitura_classifier.py` — `taxonomy_metadata()`.

**Arquivos de saída.**

- 5 handlers SP-first, parametrizados por `severidade: Literal["high","critical"]`:
  1. **`sp_severidade_overview`** — 1 linha · KPIs `total`, `procedentes`, `improcedentes`, `pct_procedentes`, `reincidentes_clientes`, `valor_medio_fatura`, `categorias_count`, `top3_share`, `delta_trimestre`.
  2. **`sp_severidade_mensal`** — série mensal `mes_ingresso`, `qtd_erros`, `procedentes`, `improcedentes`. Datas como ISO (`YYYY-MM-01`).
  3. **`sp_severidade_categorias`** — `categoria_id`, `categoria`, `vol`, `pct` ordenados desc, top-N (default 12) + bucket "Demais (k)".
  4. **`sp_severidade_causas`** — `id`, `nome`, `vol`, `proc`, `reinc`, `cat` para scatter X(volume) × Y(procedência) × tamanho(reincidência) × cor(categoria).
  5. **`sp_severidade_ranking`** — top-10 instalações reincidentes: `inst`, `cat`, `causa`, `reinc`, `valor`, `spark[]` (9 últimos meses), `cidade`.

**Contrato de registro.** Cada view registra-se com `ViewSpec(id, group_keys, metrics, FILTER_FIELDS, handler, kwargs={"severidade": ...})`. Total: **10 ViewSpecs** (5 × {alta, critica}).

**Helpers internos** (privados, prefixo `_`):

- `_attach_severidade(frame)` — merge com `taxonomy_metadata()` em `causa_canonica → classe`. Defaults seguros: `severidade=low`, `categoria=nao_classificada`, `peso_severidade=1.0`.
- `_filter_sp_severidade(frame, severidade)` — filtra `regiao=='SP'` + `severidade ∈ {high, critical}`. Aceita aliases pt-BR (`alta`, `critica`) via `_SEVERIDADE_ALIAS`.

**Riscos e mitigações.**

| Risco | Mitigação |
|---|---|
| `groupby(...).apply(_aggregate, include_groups=False)` quebra em pandas <2.2 | Manter pandas pinado em `pyproject.toml` (já está). Smoke em CI. |
| Cardinalidade do scatter > 14 | `limit=14` + bucket "outros" no handler. |
| Frame vazio (silver não baixou) | Handlers retornam DataFrame vazio com colunas corretas; front lida via empty state. |

**Validação.**

- pytest unitário cobrindo: empty frame, severidade inválida (default `low`), frame só CE (retorna vazio), aliases pt-BR, cidade fallback. Arquivo: `tests/unit/data_plane/test_sp_severidade_views.py`.
- Smoke real: `python -m scripts.smoke_sp_severidade --view sp_severidade_alta_overview` (script novo opcional `scripts/smoke_sp_severidade.py`).
- Integração: `tests/integration/test_dashboard_router.py` ganha 2 casos para a nova família.

**DoD da frente A.**

- [ ] 5 handlers + 10 ViewSpecs registrados e importáveis.
- [ ] `pytest tests/unit/data_plane/test_sp_severidade_views.py -v` 100% verde.
- [ ] `curl http://localhost:8000/v1/aggregations/sp_severidade_alta_overview` → 200 com `dataset_hash` válido em ambiente local.
- [ ] Latência p95 < 250 ms após cache aquecido (medir via Prometheus `enel_aggregation_latency_seconds`).
- [ ] `mypy src/viz/erro_leitura_dashboard_data.py` sem novos erros.
- [ ] Sem `Any` na assinatura pública dos handlers.

### Frente B — Frontend: rotas + componentes SVG

**Motivação.** O reference HTML usa SVG puro com tooltip próprio, gradientes radiais, scatter com `r` por reincidência + cor por categoria + label por nome. Recharts não cobre esse caso sem subverter a API. Implementar SVG dedicado é mais barato e dá controle de pixel — alinhado com o desejo de paridade visual exata.

**Arquivos de saída.**

- `apps/web/src/app/routes/bi.severidade.tsx` — `SeveridadeAltaRoute`, `SeveridadeCriticaRoute`, `SeveridadeScreen` (privado).
- `apps/web/src/components/bi/SeverityCharts.tsx` — `VolumeBarsChart`, `CategoriasHBars`, `CausasScatter`, `Sparkline`, helpers `fmtN/fmtMoney/fmtPct`, hook `useContainerWidth`.
- `apps/web/src/styles.css` — bloco `Severidade screens` (apenas append; não altera tokens existentes).
- `apps/web/src/main.tsx` — duas `createRoute` lazy.

**Princípio de composição.** Cada gráfico recebe **apenas dados serializáveis e callbacks**. Estado de filtro (categoria/causa selecionada) vive na rota, não no componente — alinhado com o reference e mantém a árvore SOLID. Inversion of control fica explícita: `onToggle(id)`, não `useFilterStore()` no chart.

**Tooltip.** Uma `Tooltip` interna por gráfico com state local. Evita o anti-padrão "div global mounted in App". Custo: alguns ciclos extras de render (negligenciáveis com 5 charts). Ganho: zero coupling entre gráficos, fácil de remover.

**Acessibilidade.**

- `<svg role="img" aria-label="…">` em cada gráfico;
- Categorias renderizadas como `<button>` (não `<div onClick>`) para habilitar keyboard;
- Ranking em `<table>` real, não `<div>`-grid;
- `:focus-visible` herdado do shell (`outline 2px var(--sev-primary)`).

**Riscos.**

| Risco | Mitigação |
|---|---|
| Sazonalidade vazia (mês sem ordens vira gap) | Backend completa série. Front faz fallback se vier curta. |
| Dark theme com `--sev-wash` muito claro | Override explícito por `[data-theme="dark"][data-sev=...]`. |
| `useContainerWidth` re-render thrash | `ResizeObserver` debounced via state setter (browser nativo já cumpre). |

**DoD da frente B.**

- [ ] `tsc -b && vite build` sem erros.
- [ ] `vitest run` cobre `fmtN/fmtMoney/fmtPct`, `Sparkline path`, render do scatter sem crash.
- [ ] Rotas renderizam dado real de SP via API local.
- [ ] Lighthouse desktop ≥ 95 Perf, ≥ 90 A11y.

### Frente C — Navegação e shell

- Section "Severidade" entre "Assistente" e "BI / MIS" no `Sidebar.tsx`, com 3 itens (Executivo, Alta, Crítica).
- `data-sev-nav` no `<Link>` propaga accent (âmbar para Alta, vinho para Crítica, terracota para Executivo).
- `Topbar.CRUMB_MAP` ganha 2 entradas: `/bi/severidade-alta` → `[Severidade, Alta · SP]`, `/bi/severidade-critica` → `[Severidade, Crítica · SP]`.
- `Shell.ACONCHEGANTE_ROUTES` adiciona as duas rotas.

**DoD.**

- [ ] Atalhos de teclado `2` / `3` funcionam.
- [ ] Crumb com tag de severidade aparece com cor correta em light e dark.
- [ ] Nav Section "Severidade" mostra badge "3".

### Frente D — Tipagem e contrato cliente

- `bi.severidade.tsx` declara tipos `OverviewRow`, `MonthlyRow`, `Categoria`, `Causa`, `RankingRow` espelhando o JSON do backend (números são `number`, datas `string` ISO).
- `useAggregation<T>(viewId)` continua sendo o único acesso a aggregations. Não criamos hook específico — abstração desnecessária para 5 chamadas.
- **Sem service layer no front.** Composição flat: rota chama hook, passa resultado a chart. Inverter Control e abstração de domínio ficam no backend, onde existe regra real.

**DoD.**

- [ ] Sem `any` no escopo da feature: `grep -n ': any' apps/web/src/app/routes/bi.severidade.tsx apps/web/src/components/bi/SeverityCharts.tsx` retorna vazio.
- [ ] Tipos exportados quando reusados em testes.

### Frente E — CSS · tokens severidade

Bloco novo em `styles.css` (apenas append, sem tocar tokens existentes):

- `[data-surface="aconchegante"]` ganha `--amber-deep`, `--wine`, `--ocean`, `--sev-ease`.
- `.sev-screen[data-sev="alta"|"critica"]` redefine `--sev-primary/secondary/wash/soft/gradient`.
- Hero com 2 gradientes radiais nos cantos (preserva hierarquia tipográfica do reference).
- KPI dominante com barra lateral 3 px de gradiente sev.
- HBar / Scatter / Ranking estilizados com escopo `sev-` para evitar colisão com `kpi-strip` global.

**DoD.**

- [ ] Nenhum seletor `.sev-*` vaza para fora do `.sev-screen`.
- [ ] Verificação manual em light + dark com checklist de contraste WCAG AA mínimo.
- [ ] CSS novo isolado em bloco demarcado por comentário "Severidade screens".

### Frente F — Testes E2E (Playwright)

Novo arquivo: `apps/web/e2e/severidade.spec.ts`.

Casos:

1. Navega para `/bi/severidade-alta`, verifica que KPI "Total Alta" tem valor numérico > 0.
2. Clica na primeira HBar de categoria → estado `is-active`, link "limpar filtro" surge.
3. Hover em barra mensal → tooltip surge com `mes/ano` formatado.
4. Tecla `3` → navega para crítica, breadcrumb muda para "Crítica · SP".
5. Ranking: top 3 linhas têm classe `top-3` e gradiente sev visível.
6. Tema dark via topbar: hero mantém contraste.

**DoD.**

- [ ] `npm run test:e2e -- severidade` verde em CI.
- [ ] Snapshot de regressão visual capturado em `apps/web/e2e/__screenshots__/severidade-{alta,critica}.png`.

### Frente G — Observabilidade

- `dashboard.py` router já emite `enel_aggregation_latency_seconds{view_id, cache_result}` e `enel_cache_events_total`. Os 10 novos `view_id` aparecem automaticamente.
- Novo painel `infra/grafana/dashboards/severidade.json` com:
  - linha tempo cache `HIT`/`MISS` por view;
  - heatmap p50/p95/p99 latência;
  - contador "ordens severas SP" derivado do `total` do overview.
- Alerta `infra/prometheus/alerts/severidade.yml`: `cache_miss_ratio > 0.8 over 10m` para qualquer `sp_severidade_*` view.

**DoD.**

- [ ] Painel Grafana commitado e renderizando em staging.
- [ ] Alerta `severidade_cache_degraded` ativo.
- [ ] Documentado em `docs/RUNBOOK.md` qual ação tomar se o alerta disparar.

### Frente H — Documentação

- Atualizar (ou criar) `docs/api/aggregations.md` com tabela `view_id → group_keys → metrics → kwargs` cobrindo a família.
- `docs/CONTRIBUTING.md` cita `sp_severidade_*` como exemplo canônico de view com `kwargs`.
- README do projeto adiciona screenshots Alta + Crítica em `docs/assets/severidade-{alta,critica}.png`.
- `docs/sprints/sprint-24-web-severidade-enel.md` (este arquivo) ganha seção "Release notes" no fechamento.

**DoD.**

- [ ] Tabela de views inclui `sp_severidade_*`.
- [ ] Screenshots versionados (PNG, < 300 KB cada).
- [ ] Release notes preenchidas após cutover.

---

## 5. Plano de execução por dia

A sprint cabe em 9 dias úteis com 1 dev em foco e suporte de revisão.

| Dia | Frentes | Saída esperada |
|-----|---------|----------------|
| 1   | A (handlers) | 5 handlers + helpers, smoke local |
| 2   | A (registry + tests) | 10 ViewSpecs registrados, pytest verde |
| 3   | B (charts)   | `SeverityCharts.tsx` com 4 componentes + helpers |
| 4   | B (route)    | rota `bi.severidade.tsx` ligada ao API real |
| 5   | C + E        | sidebar, shell, tokens CSS, dark mode |
| 6   | F            | suite Playwright + snapshots aceitos |
| 7   | G            | Grafana panels + alert + RUNBOOK |
| 8   | H + revisão  | docs + screenshots + autorrevisão senior |
| 9   | buffer       | bug fixes, code review, polish, demo |

---

## 6. Riscos transversais e mitigação

| Risco | Probabilidade | Impacto | Mitigação |
|-------|--------------:|--------:|-----------|
| Silver SP sem `flag_resolvido_com_refaturamento` populado | Alta | Médio | Documentar em release notes; backend lida (zero=zero); front formata |
| Cardinalidade de causas explodir após carga maior | Baixa | Baixo | `limit=14` + bucket "outros" |
| Cache stale após reingestão | Média | Médio | TTL 60 s + ETag invalidation por hash já cobre |
| Lighthouse mobile < 85 por bundle inflado | Média | Médio | Lazy route já isola; severidade chunk ~16 KB gz |
| `groupby.apply` pandas-version drift | Baixa | Alto | pin pandas em `pyproject.toml`; smoke em CI |
| CSS novo conflitando com componentes Recharts existentes | Baixa | Baixo | Escopo `.sev-*` confinado |
| Playwright instável por SVG dynamic width | Média | Baixo | Aguardar `await page.waitForLoadState('networkidle')` antes de hover |

---

## 7. Critérios de aceite (executivos)

A sprint é aceita quando, **simultaneamente**:

1. As duas rotas renderizam com dados reais SP sem erro, em ambiente local **e** em staging.
2. Ao mudar de categoria → causa → ranking, todos os componentes responsivos atualizam sem flicker > 60 ms.
3. Mudar dataset (re-rodar ingest) invalida ETag e o front re-busca sem ação manual.
4. CI verde: `pytest tests/`, `tsc -b`, `vite build`, `npm run test:e2e -- severidade`.
5. PO inspeciona Crítica vs Alta em dark e light, lado a lado com `apps/web/references/ENEL Severidade.html`: paridade visual percebida ≤ 5 % delta.
6. Métricas Prometheus presentes em Grafana: latência, cache hit-ratio, contadores volume.

---

## 8. Pós-sprint (handoff Sprint 25 e 26)

- **Sprint 25 — Severidade CE.** Portar mesmas 5 views para CE (`ce_severidade_*`) e adicionar toggle de região na top-bar das telas de severidade. Custo estimado: 2 dias.
- **Sprint 26 — RAG por ordem.** Substituir o painel "descrições identificadas pelo assistente" do reference por chamada RAG estruturada `/v1/rag/explain?ordem=...` retornando `resumo`, `sugestao`, `area`. Backend Sprint 17 já tem fundação.
- **Sprint 27 — Enrichment de UC.** `municipio` por UC alimentando `cidade` do ranking sem fallback "SP/SP".

---

## 9. Anti-patterns que esta sprint **não** introduz

- ❌ Mock data no front. Zero exceção — se o backend não devolve, a UI mostra empty state.
- ❌ Regra de severidade hard-coded em React/TS. Toda derivação vive em `taxonomy_metadata()`.
- ❌ Wrapper Recharts acima do existente. Cada novo gráfico SVG fica autocontido.
- ❌ Estado global novo. Zustand store de filtros já basta; categoria/causa ativa é local da rota.
- ❌ Endpoint `/severidade/alta` específico. Mantemos contrato genérico `/v1/aggregations/{view_id}` — mais simples e testável.
- ❌ Service layer "para o futuro" no front. YAGNI.
- ❌ `useEffect` para fetching. `useAggregation` (Tanstack Query) é o único caminho.

---

## 10. Definition of Done — sprint inteira

- [ ] Frentes A–H concluídas e marcadas individualmente.
- [ ] Code review de no mínimo 1 par senior (backend + front).
- [ ] Demo gravada em vídeo de até 3 min mostrando: navegação Alta → Crítica → cross-filter categoria → causa → ranking → tema escuro.
- [ ] Tag git `sprint-24-severidade-v1` criada.
- [ ] PR único squash-mergeado em `main` com título `feat(web): severidade SP (Alta/Crítica) · sprint 24`.
- [ ] Release notes preenchidas no fim deste arquivo.
- [ ] Feature flag `severidade_v1` abre 100 % do tráfego em staging por 48 h sem erro novo em logs.
- [ ] `docs/api/aggregations.md` reflete a nova família.
- [ ] Painel Grafana ativo e alertas configurados.

---

## 11. Apêndice — Mapeamento dos componentes do reference para a implementação

| Bloco no `ENEL Severidade.html` | Implementação Sprint 24 |
|---|---|
| Sidebar com section BI / Severidade | `Sidebar.tsx` (Frente C) |
| Topbar com crumbs + status pulse | `Topbar.tsx` (Frente C) |
| Hero com gradiente radial e métrica grande | `.sev-hero` em `styles.css` (Frente E) |
| Strip de 5 KPIs com proc/improc | `<Kpi>` + `<KpiSplit>` em `bi.severidade.tsx` (Frente B) |
| Story block com lead em itálico | `.sev-story` (Frente E) |
| Volume mensal (barras com gradiente) | `VolumeBarsChart` (Frente B) |
| Categorias HBars cross-filter | `CategoriasHBars` (Frente B) |
| Scatter causas X×Y×r×cor | `CausasScatter` (Frente B) |
| Tabela descrições assistente | **Fora do escopo · Sprint 26** |
| Ranking Top-10 com sparkline | `RankingTable` + `Sparkline` (Frente B) |
| Tweaks panel | **Fora do escopo · Sprint 27** |

---

## 12. Release notes (preencher no fechamento)

```text
- Adicionadas rotas /bi/severidade-alta e /bi/severidade-critica.
- Backend: 5 famílias × 2 severidades = 10 ViewSpecs (sp_severidade_*).
- Front: SeverityCharts.tsx (SVG nativo) + bi.severidade.tsx.
- CSS: bloco Severidade screens com tokens --sev-* via [data-sev].
- Sidebar/topbar: nav section "Severidade" + crumb tag.
- Limitação conhecida: pct_procedentes=0 até silver SP popular flag_resolvido_com_refaturamento.
- Cobertura: pytest (handlers) + Playwright (rotas + cross-filter).
```
