# Sprint 23 — Migração Completa do MVP Streamlit para Web React/TypeScript

**Executor principal**: Claude Opus 4.7  
**Modo esperado**: reasoning `medium`  
**Período sugerido**: 2 semanas  
**Precedência**: Sprint 21 (MIS Executivo Streamlit), Sprint 22 (RAG/Runtime)  
**Status alvo**: `TODO`  
**Estratégia de cutover**: faseada, com Streamlit como fallback temporário  

---

## 1. Objetivo macro

Migrar a interface principal do produto analítico de `apps/streamlit/erro_leitura_dashboard.py` para `apps/web`, entregando uma aplicação web completa em React/TypeScript com:

- paridade funcional com o Streamlit atual;
- excelência visual baseada em `apps/web/references/Refactor.html` e `apps/web/references/MIS BI Aconchegante.html`;
- consumo exclusivo de contratos backend/data plane, sem replicar regra de negócio no frontend;
- rollout faseado com fallback operacional em Streamlit até aceite final;
- estrutura modular, SOLID, limpa, testável e sustentável.

O resultado da sprint não é um protótipo web. O resultado é a **nova interface principal do produto**.

---

## 2. Contexto real do repositório

### 2.1 Interface atual em produção controlada

O MVP atual vive em `apps/streamlit/erro_leitura_dashboard.py` e já possui comportamento de produto real, não de prova de conceito. Hoje ele entrega:

- navegação principal via 9 abas;
- filtros persistentes;
- sincronização com query params;
- presets de filtro;
- storytelling executivo;
- indicadores e tabelas por camada analítica;
- assistente RAG integrado;
- visual premium baseado em design graphite/aconchegante;
- estados de loading e empty state;
- CTA contextual das telas para o assistente.

### 2.2 Abas existentes no Streamlit

As abas reais do MVP atual são:

1. `BI MIS Executivo`
2. `CE Totais`
3. `Ritmo`
4. `Padrões`
5. `Impacto`
6. `Taxonomia`
7. `Governança`
8. `Sessão Educacional`
9. `Assistente`

As implementações estão distribuídas em:

- `apps/streamlit/layers/mis.py`
- `apps/streamlit/layers/reclamacoes_ce.py`
- `apps/streamlit/layers/executive.py`
- `apps/streamlit/layers/patterns.py`
- `apps/streamlit/layers/impact.py`
- `apps/streamlit/layers/taxonomy.py`
- `apps/streamlit/layers/governance.py`
- `apps/streamlit/layers/educational.py`
- `apps/streamlit/layers/chat.py`

### 2.3 Web atual já existente

O repositório já possui embrião relevante de frontend web em `apps/web`.

Estado atual confirmado:

- stack com `Vite`, `React 18`, `TypeScript`, `TanStack Query`, `TanStack Router`, `Zustand`, `Recharts`, `Vitest`, `Playwright`;
- shell inicial implementado;
- rotas iniciais implementadas;
- integração básica com `/v1/aggregations/*`;
- chat SSE básico implementado;
- Dockerfile web já pronto;
- web já sobe em `infra/docker-compose.share.yml`.

### 2.4 Cobertura atual do web

Rotas hoje existentes:

- `/chat`
- `/bi/mis`
- `/bi/executive`
- `/bi/patterns`
- `/bi/impact`
- `/bi/taxonomy`

Lacunas confirmadas frente ao Streamlit:

- não existe `CE Totais`;
- não existe `Governança`;
- não existe `Sessão Educacional`;
- filtros globais não têm paridade com o Streamlit;
- presets ainda não existem com mesma semântica;
- CTA contextual para o assistente não existe;
- chat web ainda é simplificado frente ao chat Streamlit;
- design system web ainda está em estado scaffold, não em estado produto.

### 2.5 Backend e data plane já existentes

O backend já possui base sólida para suportar a migração:

- `src/api/main.py` publica app FastAPI principal;
- `src/api/routers/dashboard.py` expõe `/v1/dataset/version`, `/v1/aggregations/{view_id}`, `/v1/dataset/erro-leitura.arrow`, `/v1/telemetry/web-vitals`;
- `src/api/routers/rag.py` expõe `/v1/rag/cards`, `/v1/rag/stream`, `/v1/rag/feedback`;
- `src/data_plane/store.py` já centraliza acesso ao dataset;
- `src/data_plane/views.py` já possui registry declarativo extenso de views analíticas;
- `dataset_hash` já existe como chave de coerência entre cliente e servidor.

### 2.6 Infra já existente

`infra/docker-compose.share.yml` já sobe:

- `api`
- `web`
- `streamlit`
- `caddy`
- `cloudflared`

Logo, a sprint não começa do zero. Ela começa de uma base híbrida com Streamlit e web convivendo.

---

## 3. Problema que a sprint resolve

Hoje a experiência está fragmentada:

- Streamlit concentra a UX madura;
- web concentra apenas a prova inicial de consumo;
- backend/data plane já conseguem sustentar uma UI web mais séria, mas a interface final ainda não migrou;
- existe risco de manter regra de negócio espalhada entre Streamlit, web e backend se a migração for feita sem disciplina.

Os problemas-alvo são:

1. **Dependência operacional do Streamlit como UI principal**  
   O Streamlit cumpre bem o papel de MVP, mas não deve permanecer como interface definitiva.

2. **Paridade funcional incompleta no web**  
   O frontend React atual não cobre toda a superfície do produto.

3. **Paridade visual incompleta**  
   O web ainda não absorveu a qualidade visual consolidada no Streamlit e nos HTMLs de referência.

4. **Risco de lógica duplicada**  
   Se a migração for “frontend-first”, sem consolidar o data plane, a regra analítica será reimplementada em JSX.

5. **Chat web abaixo do patamar do chat Streamlit**  
   O backend SSE já existe, mas a experiência ainda não espelha pipeline, contexto, citabilidade e estados ricos.

---

## 4. Princípios obrigatórios da sprint

### 4.1 Fonte única de verdade

Toda regra analítica deve viver em:

- `src/data_plane/*`
- `src/api/services/*`
- `src/api/routers/*`

Nunca em componentes React.

### 4.2 Paridade antes de reinvenção

Antes de introduzir novos comportamentos, o web deve alcançar paridade com a experiência útil já existente no Streamlit.

### 4.3 URL-first

Filtros, navegação relevante e tema compartilhável devem viver na URL quando fizer sentido. Estado efêmero fica em store local.

### 4.4 Componentização real

Rota não faz transformação de dado. Hook não faz markup. Componente visual não conhece fetch bruto. Tokens não ficam espalhados em CSS ad hoc.

### 4.5 Rollout reversível

Não haverá corte big-bang. Streamlit permanece como fallback temporário enquanto o web assume o caminho principal.

### 4.6 Qualidade visual explícita

O objetivo não é “um dashboard React”. O objetivo é migrar o padrão de excelência visual e narrativa já validado.

---

## 5. Arquitetura atual resumida

### 5.1 Camada de apresentação

- `apps/streamlit/` contém o MVP atual;
- `apps/web/` contém a nova UI em evolução.

### 5.2 Camada de serviço

- `src/api/` contém FastAPI, middlewares, routers, schemas e services;
- `/v1/*` já funciona como superfície de consumo do web.

### 5.3 Camada de dados analíticos

- `src/data_plane/` já centraliza dataset versioning, store e registry de views;
- `src/viz/erro_leitura_dashboard_data.py` ainda sustenta parte da preparação consumida pelo Streamlit.

### 5.4 Infra

- `infra/dockerfiles/web.Dockerfile`
- `infra/dockerfiles/streamlit.Dockerfile`
- `infra/dockerfiles/Dockerfile.api`
- `infra/docker-compose.share.yml`

---

## 6. Arquitetura alvo da sprint

### 6.1 Frontend alvo

`apps/web` será a interface principal do produto com:

- shell global;
- navegação por rotas;
- filtros globais com sincronização em URL;
- telas BI/MIS completas;
- chat RAG premium;
- tema claro/escuro;
- componentes compartilhados orientados por tokens;
- testes unitários, integration e E2E.

### 6.2 Backend alvo

`src/api` permanece como gateway único do frontend.

Responsabilidades:

- servir dataset version;
- servir agregações por view;
- servir SSE do chat;
- servir feedback e telemetria;
- manter coerência por `dataset_hash`.

### 6.3 Data plane alvo

`src/data_plane` será a única origem de agregação para o frontend web.

Se alguma informação do Streamlit ainda depender de cálculo fora do data plane, a sprint deve mover esse cálculo para:

- `src/data_plane/views.py`, ou
- `src/api/services/*`

Nunca para React.

### 6.4 Infra alvo

No profile `share`, o tráfego principal deve seguir:

`caddy -> web -> api`

O container `streamlit` permanece disponível apenas como fallback operacional durante o rollout.

---

## 7. Referência visual obrigatória

### 7.1 Chat, sidebar e superfícies densas

Tomar como referência principal:

- `apps/web/references/Refactor.html`

Esse arquivo define o padrão para:

- sidebar graphite;
- tokens escuros;
- chat;
- sugestões de perguntas;
- badges;
- superfícies densas;
- visual premium técnico;
- linguagem de streaming e fontes.

### 7.2 BI executivo e storytelling

Tomar como referência principal:

- `apps/web/references/MIS BI Aconchegante.html`
- `apps/web/references/MIS Aconchegante charts.js`
- `apps/web/references/MIS Aconchegante data.js`

Esses arquivos definem o padrão para:

- hero executivo;
- warm palette;
- KPI strip;
- story blocks;
- pareto;
- health cards;
- leitura de cartões e narrativa analítica;
- relação CE/SP via tons terra/plum;
- tipografia serifada para valor e narrativa.

### 7.3 Tokens finais da aplicação

A sprint deve consolidar um design system híbrido:

- `Inter Tight` para headings técnicos e chat premium;
- `Fraunces` para hero executivo, KPIs dominantes e narrativa;
- `Inter` para corpo e UI;
- `JetBrains Mono` para dataset hash, badges, métricas, atalhos e números;
- `oklch` como padrão de cor onde aplicável;
- tokens centralizados em módulo único e refletidos em CSS global.

---

## 8. Escopo da sprint

### 8.1 Em escopo

- migração completa da experiência principal do Streamlit para web;
- criação das rotas faltantes;
- design system completo do web;
- filtros e presets com paridade;
- chat web avançado;
- CTA contextual entre BI e chat;
- ajustes necessários em API/data plane para cobrir paridade;
- atualização dos fluxos Docker/share;
- atualização de runbook e documentação operacional;
- aceitação via testes e smoke real.

### 8.2 Fora de escopo

- reescrever backend inteiro;
- introduzir nova camada de autenticação corporativa;
- reescrever modelos ML/RAG;
- descontinuar Streamlit antes do aceite final;
- redesign livre que ignore as referências aprovadas;
- mover BI para Next.js ou outro framework;
- reconstruir Superset ou outras camadas fora do foco.

---

## 9. Estratégia de migração

### 9.1 Modelo adotado

Cutover faseado.

### 9.2 Regras do modelo faseado

1. O web passa a ser a interface alvo da sprint.
2. Streamlit permanece disponível como fallback.
3. O tráfego principal do profile `share` migra para web ao final da sprint.
4. A remoção do Streamlit do caminho principal só acontece após checklist de aceite.
5. O código Streamlit não será apagado nesta sprint. Será despriorizado operacionalmente.

### 9.3 Critério de saída do fallback

O Streamlit só deixa de ser fallback quando houver:

- paridade funcional validada;
- chat validado;
- visual validado;
- smoke Docker validado;
- rotas faltantes entregues;
- runbook atualizado;
- aceitação explícita da nova UI como principal.

---

## 10. Frentes de trabalho

## Frente A — Inventário definitivo de paridade

### Objetivo

Produzir matriz de migração `Streamlit -> Web -> API/Data Plane`.

### Entregáveis

- mapa das 9 abas do Streamlit;
- mapa das rotas web equivalentes;
- mapa dos endpoints e `view_id` usados por cada tela;
- lista dos comportamentos ainda exclusivos de Streamlit.

### Regras

- qualquer comportamento sem equivalente web deve virar item explícito do backlog;
- qualquer cálculo exclusivo de Streamlit deve ser movido para backend/data plane antes da tela final.

### Saída esperada

Tabela interna no documento da sprint com colunas:

- área;
- origem Streamlit;
- destino web;
- contrato consumido;
- status de paridade;
- gap.

---

## Frente B — Shell, navegação e layout base do web

### Objetivo

Transformar `apps/web/src/components/shared/Shell.tsx` em shell definitivo da aplicação.

### Mudanças

- sidebar completa com 9 destinos;
- topo com dataset version, tema e controles globais;
- padrão visual graphite/aconchegante conforme contexto de tela;
- navegação responsiva desktop/mobile;
- layout robusto para telas densas;
- suporte consistente a dark/light.

### Arquivos-alvo principais

- `apps/web/src/components/shared/Shell.tsx`
- `apps/web/src/styles.css`
- `apps/web/src/lib/tokens.ts`
- `apps/web/src/state/ui-store.ts`

### Decisões obrigatórias

- sidebar é parte do app shell e não de cada rota;
- estado de abrir/fechar sidebar fica em zustand;
- tema pode vir de query param e preferência do usuário;
- conteúdo principal precisa suportar páginas BI densas e chat largo.

---

## Frente C — Sistema de filtros, presets e URL state

### Objetivo

Migrar para web o comportamento real de filtros hoje existente em `apps/streamlit/components/filters.py`.

### Capacidades obrigatórias

- filtros globais por região, causa, tópico e período;
- flag de refaturamento;
- suporte a `include_total`;
- presets equivalentes ao Streamlit;
- sincronização bidirecional com query params;
- chips de filtros ativos;
- resumo do universo filtrado;
- persistência de compartilhamento por URL.

### Presets obrigatórios

- `Manual`
- `Últimos 30 dias`
- `CE · Grupo operacional`
- `Ordens com refaturamento`

### Arquivos-alvo principais

- `apps/web/src/hooks/*`
- `apps/web/src/state/*`
- `apps/web/src/lib/api.ts`
- novos componentes em `apps/web/src/components/shared/*`

### Regra de implementação

Replicar a semântica do Streamlit, não apenas o visual.

---

## Frente D — Paridade BI/MIS por rota

### Objetivo

Entregar todas as áreas analíticas hoje existentes no Streamlit.

### Rotas obrigatórias finais

- `/chat`
- `/bi/mis`
- `/bi/ce-totais`
- `/bi/executive`
- `/bi/patterns`
- `/bi/impact`
- `/bi/taxonomy`
- `/bi/governance`
- `/bi/educational`

### 1. MIS Executivo

Migrar para composição premium:

- hero;
- KPIs dominantes;
- gráficos de volume por região;
- resumos regionais;
- storytelling inicial;
- CTA para assistente contextual.

Base principal:

- `view_id=mis`
- `view_id=overview`
- views auxiliares já existentes no data plane quando necessário.

### 2. CE Totais

Criar nova rota equivalente ao comportamento de `apps/streamlit/layers/reclamacoes_ce.py`.

Requisitos:

- leitura específica de reclamação total CE;
- paridade com visão já existente;
- CTA contextual para assistente;
- nada de cálculo exclusivo no client.

Se faltarem views no data plane, adicioná-las em `src/data_plane/views.py`.

### 3. Ritmo

Migrar comportamento de `apps/streamlit/layers/executive.py` para tela mais madura visualmente.

### 4. Padrões

Migrar comportamento de `apps/streamlit/layers/patterns.py`.

### 5. Impacto

Migrar comportamento de `apps/streamlit/layers/impact.py`.

### 6. Taxonomia

Migrar comportamento de `apps/streamlit/layers/taxonomy.py`.

### 7. Governança

Criar rota nova equivalente a `apps/streamlit/layers/governance.py`.

Componentes esperados:

- health cards;
- status labels;
- narrativa de segurança/contratos;
- CTA contextual para assistente.

### 8. Sessão Educacional

Criar rota nova equivalente a `apps/streamlit/layers/educational.py`.

Componentes esperados:

- explicação do fluxo analítico;
- narrativa pedagógica;
- ligação clara com BI e RAG;
- CTA contextual para assistente.

---

## Frente E — Chat RAG premium no web

### Objetivo

Levar o chat web ao mesmo patamar funcional do Streamlit, usando backend SSE já existente.

### Estado atual

O web já possui:

- `apps/web/src/components/chat/ChatPanel.tsx`
- `apps/web/src/hooks/useRagStream.ts`
- `apps/web/src/lib/sse.ts`

Mas ainda está simplificado frente a `apps/streamlit/layers/chat.py`.

### Capacidades obrigatórias finais

- streaming token a token;
- perguntas sugeridas;
- contexto herdado da área atual;
- histórico de sessão;
- feedback útil/não útil;
- badge de cache;
- estados vazios/erro;
- indicadores de pipeline/thinking;
- estrutura preparada para exibir citações e metadados;
- ergonomia desktop/mobile;
- copy e layout condizentes com `Refactor.html`.

### Mudanças de contrato obrigatórias

`/v1/rag/stream` e cliente SSE devem suportar `context_hint`.

O frontend deve enviar:

- `question`
- `history`
- `context_hint`
- `X-Dataset-Version`

### Arquivos-alvo principais

- `apps/web/src/components/chat/ChatPanel.tsx`
- `apps/web/src/hooks/useRagStream.ts`
- `apps/web/src/lib/sse.ts`
- `src/api/routers/rag.py`
- `src/api/services/rag_stream.py`

### Regra de qualidade

O chat web não pode regredir frente ao Streamlit em:

- contexto;
- feedback;
- estabilidade;
- coerência com dataset;
- clareza visual.

---

## Frente F — Backend e data plane para paridade total

### Objetivo

Completar o backend e o data plane apenas onde necessário para a nova UI, sem criar acoplamento ad hoc.

### Mudanças obrigatórias

- revisar gaps de `view_id` para `CE Totais`, `Governança` e `Sessão Educacional`;
- criar views faltantes em `src/data_plane/views.py` quando não houver cobertura;
- manter `DataStore.aggregate()` como porta oficial;
- garantir que toda tela web tenha backend suficiente sem depender de cálculo em React;
- formalizar, quando fizer sentido, tipos e contratos mais claros para agregações consumidas pelo web.

### Regra de implementação

Se um dado hoje só existe via função interna do layer Streamlit:

1. mover para data plane ou serviço;
2. cobrir via endpoint já existente ou endpoint novo minimamente necessário;
3. consumir no web.

Não copiar cálculo para o componente.

---

## Frente G — Design system compartilhado do web

### Objetivo

Substituir o CSS atual scaffolding por um sistema visual coeso e reutilizável.

### Componentes obrigatórios

- shell/sidebar;
- topbar;
- KPI card;
- KPI strip;
- hero executivo;
- story block;
- insight callout;
- pareto list;
- health cards;
- topic pills;
- table section;
- chart section;
- empty state;
- skeleton;
- message bubble;
- feedback row;
- suggestion cards;
- filter chips.

### Arquivos-alvo principais

- `apps/web/src/styles.css`
- `apps/web/src/lib/tokens.ts`
- novos componentes em `apps/web/src/components/*`

### Regra de implementação

- tokens primeiro;
- componentes depois;
- telas por último.

---

## Frente H — Docker, share e operação

### Objetivo

Tornar o web a interface principal também do fluxo operacional.

### Mudanças obrigatórias

- ajustar `infra/docker-compose.share.yml` para que o `caddy` sirva web como frontend principal;
- manter `streamlit` como fallback temporário;
- revisar `infra/nginx/enel.conf` para SPA routing, cache headers e comportamento adequado;
- confirmar health check do web;
- confirmar ordem de subida e dependências.

### Documentação a atualizar

- `docs/RUNBOOK.md`
- `docs/SHARE_DASHBOARD.md`

### Regras

- rollback precisa ser simples;
- não quebrar a stack de share durante a transição;
- URL pública deve passar a apontar a UI web.

---

## 11. Backlog técnico detalhado

### Épico 1 — Paridade estrutural do frontend

1. Expandir o router para 9 áreas de produto.
2. Refatorar shell para suportar navegação completa.
3. Criar organização final de componentes por domínio.
4. Consolidar tokens e tema.

### Épico 2 — Filtros globais e estado compartilhável

1. Implementar estado de filtros com paridade funcional.
2. Implementar URL sync.
3. Implementar presets.
4. Implementar chips e resumo filtrado.

### Épico 3 — BI completo

1. Levar MIS para nível premium.
2. Criar `CE Totais`.
3. Migrar `Ritmo`, `Padrões`, `Impacto`, `Taxonomia`.
4. Criar `Governança`.
5. Criar `Sessão Educacional`.

### Épico 4 — Chat premium

1. Reestruturar `ChatPanel`.
2. Evoluir `useRagStream`.
3. Evoluir SSE client.
4. Adaptar backend para `context_hint` e eventos ricos.

### Épico 5 — Data plane e API

1. Fechar gaps de views.
2. Garantir ausência de regra analítica no client.
3. Ajustar contratos tipados.

### Épico 6 — Operação e cutover

1. Ajustar compose/share/nginx.
2. Atualizar docs operacionais.
3. Executar rollout faseado.

---

## 12. Mudanças de interface, contrato e tipos

### 12.1 Rotas novas obrigatórias

Adicionar:

- `/bi/ce-totais`
- `/bi/governance`
- `/bi/educational`

### 12.2 Contrato de filtros

O web deve suportar a mesma semântica funcional já existente no Streamlit:

- `regiao`
- `causa`
- `topico`
- `inicio`
- `fim`
- `refat`
- `total`
- `theme`

### 12.3 Contrato do chat

`POST /v1/rag/stream` deve aceitar:

- `question`
- `history`
- `context_hint`

Header obrigatório:

- `X-Dataset-Version`

### 12.4 Dataset version

`dataset_hash` continua sendo a referência para:

- invalidação de queries;
- coerência entre BI e chat;
- cache HTTP;
- detecção de cliente stale.

### 12.5 Views analíticas

Qualquer tela nova deve ser alimentada por `view_id` do data plane.

Se a view não existir:

- criar em `src/data_plane/views.py`;
- expor via `/v1/aggregations/{view_id}`;
- tipar no web.

---

## 13. Ordem recomendada de implementação

1. Consolidar doc e matriz de paridade.
2. Refatorar shell, tokens e layout base.
3. Implementar filtros globais e presets.
4. Ajustar router e navegação completa.
5. Completar telas BI faltantes.
6. Refatorar telas já existentes para padrão premium.
7. Evoluir chat web e SSE.
8. Fechar gaps de backend/data plane.
9. Ajustar Docker/share/nginx.
10. Atualizar docs operacionais.
11. Executar validação completa.
12. Fazer cutover faseado.

---

## 14. Plano de testes

### 14.1 Testes frontend unitários

Cobrir:

- shell;
- sidebar;
- filtros;
- presets;
- chips;
- adapters;
- hooks de dataset/version;
- `useRagStream`;
- feedback do chat;
- parsing de query params.

### 14.2 Testes frontend de integração

Cobrir:

- render de cada rota;
- invalidação por mudança de `dataset_hash`;
- tema;
- CTA contextual;
- persistência de filtros por URL;
- estados de loading/empty/error.

### 14.3 Testes E2E com Playwright

Cobrir desktop e mobile:

1. abrir home;
2. navegar entre áreas;
3. aplicar filtros;
4. usar presets;
5. abrir rota por deep-link;
6. enviar pergunta no chat;
7. validar feedback;
8. validar responsividade básica;
9. validar fallback de erro.

### 14.4 Testes backend/API

Cobrir:

- novos `view_id`;
- contratos do `/v1/rag/stream`;
- coerência com `X-Dataset-Version`;
- respostas de erro bem formadas;
- `dataset/version`.

### 14.5 Testes de paridade funcional

Para cada área migrada, validar:

- KPI principal;
- tabela principal;
- gráfico principal;
- CTA contextual para o chat, quando aplicável.

### 14.6 Smoke operacional

Validar:

- `api`
- `web`
- `caddy`
- `cloudflared`
- fallback Streamlit

---

## 15. Critérios de aceite

A sprint só pode ser marcada como concluída se todos os itens abaixo forem verdadeiros:

1. O web cobre as 9 capacidades hoje existentes no Streamlit.
2. O web é visualmente coerente com `Refactor.html` e `MIS BI Aconchegante.html`.
3. Nenhuma regra analítica relevante permanece exclusiva do layer Streamlit.
4. O chat web suporta contexto, streaming e feedback com qualidade equivalente ou superior ao Streamlit.
5. Os filtros e presets do web têm paridade semântica com os do Streamlit.
6. O `share` profile expõe o web como interface principal.
7. O Streamlit permanece apenas como fallback temporário, não como UI principal.
8. Runbook e documentação de compartilhamento foram atualizados.
9. Testes essenciais do frontend e backend estão verdes.
10. Smoke de stack web foi executado com sucesso.

---

## 16. Rollout

### 16.1 Passos

1. Entregar web com paridade completa.
2. Validar localmente.
3. Validar profile `share`.
4. Apontar `caddy` para web principal.
5. Manter Streamlit disponível.
6. Monitorar uso e estabilidade.
7. Encerrar fallback apenas após aceite final.

### 16.2 Observabilidade mínima

Monitorar:

- disponibilidade do `api`;
- disponibilidade do `web`;
- erros de SSE;
- falhas de agregação;
- regressão visual crítica;
- métricas de web vitals quando disponíveis.

---

## 17. Rollback

Se o web principal falhar após cutover:

1. restaurar roteamento principal para Streamlit no profile de share;
2. manter `api` e `web` ativos para diagnóstico;
3. preservar artefatos e logs;
4. corrigir problema sem apagar a trilha da migração.

O rollback precisa ser simples e documentalmente explícito.

---

## 18. Riscos e mitigação

### Risco 1 — Lacunas de paridade escondidas no Streamlit

**Mitigação**: matriz de paridade obrigatória antes da implementação pesada.

### Risco 2 — Regras analíticas escaparem para o client

**Mitigação**: revisão explícita de qualquer transformação feita em rota/componente.

### Risco 3 — Chat web continuar inferior ao Streamlit

**Mitigação**: tratar o chat como frente própria, não como detalhe de tela.

### Risco 4 — Design virar mistura incoerente

**Mitigação**: tokens centralizados e referências explícitas por contexto de tela.

### Risco 5 — Cutover quebrar compartilhamento público

**Mitigação**: manter Streamlit como fallback e validar compose/share antes do corte.

---

## 19. Definition of Done desta sprint

Considerar a sprint concluída apenas quando:

- MD da sprint estiver alinhado com implementação;
- frontend web estiver completo e modular;
- backend/data plane cobrirem todas as telas;
- compose/share estiver ajustado;
- runbook estiver atualizado;
- smoke operacional tiver sido executado;
- Streamlit deixar de ser a interface principal.

---

## 20. Resultado esperado ao fim da sprint

Ao final desta sprint, o projeto deve operar assim:

- `apps/web` é a UI principal oficial;
- `src/api` e `src/data_plane` são a espinha dorsal da experiência;
- Streamlit deixa de ser o centro do produto e vira fallback temporário;
- BI, MIS e chat convivem numa interface React/TypeScript única, premium, modular e sustentável;
- a base fica pronta para evolução futura sem novo acoplamento à arquitetura do Streamlit.

