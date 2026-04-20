Abaixo está a **Sprint 21 complementada e consolidada**, já trazendo o foco para **excelência do MVP em Streamlit**, **BI/MIS**, **refactor de frontend**, **correção de bugs frontend/backend**, **sidebar mais forte**, **storytelling executivo**, e **aderência à arquitetura atual**.

---

# Sprint 21 — MIS Executivo, Causa-Raiz & Excelência do MVP Streamlit (CE Focus)

**Responsável executor**: Principal Analytics Engineer / Data Engineering / Produto
**Período**: 2026-05-25 → 2026-06-05 (2 semanas)
**Precedência**: Sprint 20 (RAG Agents & Evaluation)
**Status alvo**: `TODO`

## Diretriz central da sprint

> **Priorizar o desenvolvimento do Streamlit como MVP da plataforma analítica é diretriz central desta sprint.** Toda decisão de produto, frontend, backend, modelagem analítica e storytelling executivo deve ser subordinada à entrega de um MVP sólido, confiável, visualmente maduro, aderente ao padrão institucional da ENEL e orientado a BI/MIS acionável.

---

## 1. Objetivo Macro

Ingerir, normalizar e classificar semanticamente o histórico de reclamações operacionais do Ceará (`DESCRICOES_ENEL/reclamacoes_total*.xlsx`), transformando descrições de texto livre (sintomas) em uma taxonomia executiva estável (causas-raiz), e **materializar essa inteligência em um MVP Streamlit de padrão sênior**, com foco em:

* MIS executivo
* BI operacional acionável
* narrativa analítica orientada à decisão
* visual institucional coerente com ENEL
* excelente experiência de uso
* estabilidade end-to-end entre dados, backend e frontend

O Streamlit é tecnicamente adequado para esse papel de MVP porque suporta **apps multipágina**, **estado entre páginas**, **tabs**, **theming**, **customização específica da sidebar**, **conexões com dados/APIs** e **caching**, o que o torna suficiente para uma camada analítica executiva inicial sem exigir, neste momento, um frontend web mais pesado. ([Streamlit Docs][1])

---

## 2. Problema de Negócio

Atualmente, a diretoria e a coordenação não conseguem agir eficientemente sobre o volume de reclamações do CE. Os dados brutos focam no **sintoma relatado** e não evidenciam com clareza a **causa-raiz operacional**. Isso reduz a capacidade de:

* atacar falhas estruturais
* priorizar times e prestadoras
* identificar perdas financeiras
* monitorar reincidência
* apresentar leitura executiva consistente do problema

Além disso, o projeto ainda precisa converter a inteligência analítica em uma **camada de consumo madura**, com UX clara, leitura rápida, drill-down útil e narrativa coerente com o fluxo real do dado.

No âmbito institucional, a ENEL Brasil vem reforçando sua identidade visual no país com uma marca inspirada nas cores da bandeira do Brasil e com discurso de proximidade, evolução operacional e melhoria contínua do atendimento. Isso reforça a necessidade de um MVP analítico com linguagem visual mais confiável, clara e corporativa, sem improvisação estética. ([Enel Brasil][2])

---

## 3. Reposicionamento Estratégico da Sprint

A sprint original está correta no eixo de dados, mas precisa de um reposicionamento:

### Antes

* foco principal em ingestão, classificação e API
* frontend tratado quase como consumidor passivo
* layout/UX do frontend fora de escopo

### Agora

* **o Streamlit passa a ser o MVP prioritário da plataforma**
* BI/MIS passam a ser eixo central de produto
* refactor do frontend entra em escopo
* bugs frontend/backend entram em escopo explícito
* a narrativa executiva e operacional passa a ser tratada como parte do produto
* a sidebar, navegação, legibilidade e leitura visual passam a ser itens de aceite

---

## 4. Hipóteses e Premissas

1. **Regra de Pareto Operacional:** Mais de 50% das reclamações de “Refaturamento & Cobrança” no CE decorrem de um conjunto reduzido de falhas processuais, com alta concentração em leitura/digitação, faturamento por média e ajustes corretivos.

2. **Separação Sintoma vs Causa:** `OBSERVAÇÃO ORDEM` e `DEVOLUTIVA` concentram os sinais mais fortes de causa real; `ASSUNTO` tende a refletir a taxonomia de atendimento, não necessariamente a origem do defeito.

3. **Classificação Híbrida (RegEx + LLM):** Regras determinísticas resolvem a maior parte dos casos; LLM local entra apenas como fallback controlado.

4. **Arquitetura Analítica Mantida:** Bronze/Silver/Gold + dbt + FastAPI + orquestração continuam válidos; o que muda é a **prioridade da camada Streamlit** como face do produto.

5. **Streamlit como Produto, não só Protótipo:** O Streamlit não será tratado como mock ou demo. Ele será tratado como **MVP executivo-operacional em produção controlada**, explorando navegação multipágina, estado, theming, sidebar customizada, tabs, caching e conectividade segura com dados. ([Streamlit Docs][1])

6. **Contrato Visual Evolutivo:** `MIS BI Aconchegante.html`, `Refactor.html` e os 2 arquivos JS relacionados ao “Aconchegante” deixam de ser apenas referência estática e passam a ser **insumo de refactor visual, navegação, storytelling e semântica de interface** para o Streamlit.

---

## 5. Escopo e Fora de Escopo

### Em Escopo

* **Ingestão (Bronze):** leitura e unificação dos arquivos `.xlsx` de CE.
* **Normalização e PII (Silver):** sanitização de dados sensíveis.
* **Engenharia de Features (Silver):** `macrotema`, `causa_raiz_inferida`, `ind_refaturamento`, `is_root_cause`, `criticidade`, `reincidencia_sinal`, `acionabilidade`.
* **Modelagem (Gold):** agregações orientadas ao consumo de BI/MIS.
* **API (FastAPI):** endpoints estáveis para consumo analítico.
* **MVP Streamlit:** desenvolvimento/refactor do frontend principal da plataforma analítica.
* **Refactor visual e UX:** sidebar, hierarquia de informação, filtros, grids, storytelling, estados de loading, empty states, error states.
* **Correção de bugs frontend e backend:** renderização, inconsistência de payload, tempo de resposta, estados quebrados, filtros, gráficos e navegação.
* **Observabilidade funcional do MVP:** logging, tratamento de exceções e comportamento previsível.

### Fora de Escopo

* Reescrita completa para outro framework frontend.
* Generalização para todos os estados além de CE nesta sprint.
* Profundidade pesada em Ouvidoria/Jurídico como eixo central.
* Polimento pixel-perfect baseado em brand book fechado da ENEL, caso o guia oficial detalhado não esteja disponível no repositório.

---

## 6. Arquitetura-Alvo da Sprint

### Camada de dados

* `DESCRICOES_ENEL/reclamacoes_total*.xlsx`
* Bronze consolidado
* Silver com limpeza, taxonomia e sinais de causa-raiz
* Gold com marts analíticos prontos para consumo

### Camada de serviço

* FastAPI servindo contratos estáveis
* payloads voltados a componentes analíticos e filtros

### Camada de apresentação

* **Streamlit como MVP principal**
* páginas orientadas a leitura executiva e operacional
* componentes guiados pelo contrato semântico, não por improviso visual

### Referências de frontend

* `MIS BI Aconchegante.html`
* `Refactor.html`
* os 2 arquivos JS ligados ao “Aconchegante”

### Princípio arquitetural

**Não quebrar a arquitetura atual; elevar a camada de consumo.**
O Streamlit deve refletir com clareza a lógica Bronze/Silver/Gold/API, e não mascarar inconsistências do backend com remendos visuais.

---

## 7. Frentes de Trabalho da Sprint

### Frente A — Data Discovery e entendimento do contexto atual do Streamlit

**Objetivo:** entender profundamente o que o Streamlit atual já carrega, como navega, de onde lê dados, que páginas possui, que filtros usa, que estados controla e onde estão os bugs.

**Ações**

* mapear páginas, componentes, blocos, filtros e fluxo de navegação do Streamlit atual
* mapear dependências de dados por tela
* mapear bugs atuais de frontend
* mapear falhas de contrato com backend
* identificar gargalos de tempo de carregamento
* identificar duplicidades visuais e inconsistências de layout

**Artefato**

* inventário do MVP atual
* bug map frontend/backend
* mapa de contratos API → Streamlit

---

### Frente B — Pipeline de ingestão e tratamento

Mantém a espinha dorsal da sprint original, com ampliação das features analíticas.

**Ações**

* consolidar arquivos `reclamacoes_total*.xlsx`
* padronizar schema
* tratar PII
* enriquecer atributos de negócio

**Novas colunas recomendadas**

* `criticidade_operacional`
* `acionabilidade`
* `sintoma_vs_causa_flag`
* `grupo_origem_provavel`
* `sinal_reincidencia`
* `impacto_financeiro_estimado_flag`

**Critério de aceite**

* dados consolidados com rastreabilidade e sem perda semântica relevante

A proteção de dados deve permanecer como requisito estrutural, já que a ENEL afirma adotar padrões elevados de segurança e gestão de dados pessoais em sistemas e aplicativos de TI. ([Enel Brasil][3])

---

### Frente C — Regras de negócio e taxonomia executiva

**Objetivo:** sair de texto livre para uma leitura executiva acionável.

**Regras prioritárias**

* separar sintoma de causa-raiz
* consolidar sinônimos
* agrupar descrições em macrocausas
* identificar improcedência real vs ajuste corretivo
* identificar problemas de leitura, cadastro, faturamento, medição, entrega e atendimento
* identificar itens acionáveis vs ruído

**Saídas esperadas**

* N1 = Macrotema
* N2 = Causa-raiz
* N3 = Subcausa operacional
* flags de refaturamento, improcedência, criticidade e reincidência

---

### Frente D — Modelagem Gold orientada a BI/MIS

**Objetivo:** modelar para decisão, não só para armazenamento.

**Artefatos**

* `fct_reclamacoes_classificadas`
* `agg_mis_macrotemas_mensal`
* `agg_mis_causas_pareto`
* `agg_mis_reincidencia`
* `agg_mis_refaturamento_impacto`
* `agg_mis_criticidade_operacional`
* `agg_mis_backlog_status`
* `agg_mis_origem_provavel`

**Visões-chave**

* tendência temporal
* pareto de causas
* concentração por macrotema
* impacto financeiro presumido
* reincidência
* improcedência
* criticidade
* eficiência operacional

---

### Frente E — Backend e estabilidade de contratos

**Objetivo:** garantir que o frontend Streamlit não carregue inconsistência estrutural.

**Ações**

* revisar endpoint `/mis-aconchegante`
* normalizar contratos de resposta
* reduzir payloads excessivos
* separar endpoints por blocos analíticos quando necessário
* padronizar nomes de campos
* tratar erros de forma previsível
* implementar cache estratégico no backend e/ou camada de consulta

**Critérios de aceite**

* endpoint estável
* payload coerente com o frontend
* sem quebra silenciosa de filtros
* tempos consistentes de resposta

---

### Frente F — Excelência do MVP Streamlit (core da sprint)

**Objetivo:** transformar o Streamlit em uma experiência de BI/MIS sênior.

Como o Streamlit oferece multipage apps, session state entre páginas, tabs, theming e controles de sidebar, a sprint deve explorar essas capacidades diretamente no MVP. ([Streamlit Docs][1])

**Ações obrigatórias**

* refatorar a navegação principal
* redesenhar a sidebar para alta legibilidade e presença visual
* reorganizar a hierarquia dos painéis
* melhorar leitura de KPIs, gráficos e tabelas
* corrigir estados de loading
* corrigir estados vazios
* corrigir estados de erro
* revisar filtros globais vs locais
* revisar responsividade útil dentro do contexto Streamlit
* revisar contraste, destaque visual e densidade informacional
* padronizar containers e espaçamentos
* remover poluição visual
* tornar a leitura mais executiva e menos “dashboard cru”

**Requisitos específicos da sidebar**

* visual mais institucional
* mais contraste e presença
* agrupamento lógico de filtros
* filtros mais compreensíveis
* navegação evidente
* destaque claro da página atual
* leitura rápida por diretoria e coordenação

O theming do Streamlit permite configuração global e também customização específica da sidebar, o que justifica tratá-la como item explícito de design e aceite. ([Streamlit Docs][4])

---

### Frente G — Storytelling analítico e narrativa de negócio

**Objetivo:** fazer o dashboard “contar a história certa”.

A narrativa do MVP deve seguir a arquitetura analítica, nesta ordem:

1. **Panorama executivo**

   * volume total
   * tendência
   * macrotemas dominantes
   * impacto presumido

2. **Onde está o problema**

   * concentração por macrotema
   * pareto de causas
   * severidade
   * criticidade

3. **Por que o problema acontece**

   * causa-raiz
   * subcausa
   * origem provável
   * reincidência
   * improcedência

4. **Quanto isso dói**

   * refaturamento
   * impacto financeiro presumido
   * backlog
   * volume recorrente

5. **Onde agir primeiro**

   * ranking de causas
   * frentes operacionais
   * ações prioritárias
   * quick wins

6. **Acompanhamento**

   * tendência após ação
   * queda de reincidência
   * efetividade de correção

**Princípio**
O dashboard não deve ser apenas bonito; deve conduzir a leitura executiva do sintoma até a decisão.

---

## 8. Regras de Negócio: Taxonomia Alvo (MIS/BI)

### Macrotemas N1

1. Refaturamento & Cobrança
2. Religação & Multas
3. Geração Distribuída (GD)
4. Ouvidoria & Jurídico
5. Variação de Consumo
6. Faturamento por Média/Estim.
7. Entrega da Fatura
8. Outros

### Causas-raiz N2

* `digitacao`
* `refaturamento_corretivo`
* `leitura_estimada_media`
* `medidor_danificado`
* `leitura_confirmada_improced`
* `cadastro_inconsistente`
* `erro_processual_faturamento`
* `nao_execucao_campo`
* `prazo_fluxo_operacional`
* `causa_indefinida`

### Regras complementares

* `ASSUNTO` não define sozinho causa-raiz
* `OBSERVAÇÃO ORDEM` e `DEVOLUTIVA` têm precedência analítica
* improcedência não elimina valor analítico; pode sinalizar falha de comunicação, baixa confiança do cliente ou problema de percepção
* OUV/Jurídico permanece dimensão secundária, não eixo principal de leitura

---

## 9. Entregáveis e Etapas (revisados)

### Etapa 1 — Inventário técnico do Streamlit e arquitetura de consumo

* mapear páginas, widgets, estado, filtros, bugs e contratos atuais
* documentar dependência entre Streamlit, API e marts

### Etapa 2 — Pipeline Bronze

* criar/ajustar `src/ingestion/pipeline_mis_ce.py`
* consolidar Excel em parquet

### Etapa 3 — Silver + regras determinísticas

* PII
* taxonomia
* features analíticas

### Etapa 4 — LLM fallback

* inferência apenas para indefinidos
* uso batch controlado

### Etapa 5 — Gold orientada a BI/MIS

* marts adicionais para reincidência, criticidade, impacto e origem

### Etapa 6 — Backend / FastAPI

* reforço do endpoint `/mis-aconchegante`
* eventual segmentação em endpoints menores se necessário

### Etapa 7 — Refactor do MVP Streamlit

* sidebar
* layout
* experiência de filtros
* estados visuais
* storytelling
* gráficos
* legibilidade executiva

### Etapa 8 — Hardening e bugfix

* bugs frontend
* bugs backend
* contratos quebrados
* testes manuais e técnicos
* verificação de consistência analítica

---

## 10. Critérios de Aceite

### Dados

* cobertura de classificação > 85%
* “Outros/Indefinidos” < 15%
* taxonomia consistente por amostragem validada

### Backend

* endpoint(s) estáveis
* erro tratado explicitamente
* latência adequada para uso interativo

### Streamlit / Produto

* fluxo principal sem quebra
* sidebar legível, visível e útil
* páginas com hierarquia clara
* filtros coerentes
* gráficos compreensíveis
* estados de loading/erro/empty state tratados
* storytelling perceptível do resumo executivo até a causa-raiz
* leitura alinhada a MIS e BI, não só a exploração técnica

---

## 11. Métricas de Sucesso

1. **Cobertura de classificação** > 85%
2. **Tempo de resposta percebido do MVP** compatível com uso gerencial interativo
3. **Queda de ruído analítico** por redução de “Outros/Indefinidos”
4. **Clareza executiva do dashboard** validada por leitura orientada a decisão
5. **Redução de bugs visíveis** em navegação, filtros, contratos e renderização
6. **Capacidade do MVP de responder perguntas-chave**, como:

   * quais macrocausas dominam CE?
   * o que mais gera refaturamento?
   * onde está a maior recorrência?
   * o que parece improcedente?
   * onde agir primeiro?

---

## 12. Quick Wins

* heatmap/severidade evidenciando concentração por causa
* pareto executivo de causas-raiz
* bloco de “onde agir primeiro”
* ranking de impacto/refaturamento
* sidebar reformulada para navegação clara
* primeira versão do Streamlit com cara real de produto interno

---

## 13. Riscos e Mitigações

### Risco

Inferência LLM em histórico amplo ficar cara/lenta em CPU.

### Mitigação

LLM apenas em fallback e/ou recorte recente.

### Risco

Frontend Streamlit mascarar problemas estruturais do backend.

### Mitigação

mapa de contrato API ↔ Streamlit e hardening por camada.

### Risco

Refactor visual virar esforço cosmético.

### Mitigação

todo item de UX deve estar vinculado a leitura, decisão, confiança e velocidade cognitiva.

### Risco

Tentar “imitar ENEL” sem base institucional suficiente.

### Mitigação

usar linguagem institucional coerente e só materializar tokens visuais explicitamente disponíveis; não inventar brand book fechado.

---

## 14. Resultado esperado ao final da sprint

Ao final da Sprint 21, o projeto deve entregar não apenas uma taxonomia de causa-raiz para CE, mas um **MVP Streamlit de padrão sênior**, funcionalmente sólido, visualmente confiável, aderente ao contexto institucional, e capaz de transformar reclamações operacionais em leitura executiva, tática e operacional.

---

## 15. Resumo executivo final

A sprint original estava forte em dados, mas subdimensionava o papel da camada de consumo.
A versão complementada corrige isso.

O novo foco é:

* **Streamlit como MVP prioritário**
* **BI/MIS como produto**
* **refactor de frontend em escopo**
* **correção de bugs frontend/backend**
* **sidebar como elemento crítico de UX**
* **storytelling analítico como requisito funcional**
* **aderência à arquitetura atual, sem ruptura desnecessária**

Se quiser, no próximo passo eu posso te devolver isso em um formato ainda mais operacional, como **sprint pronta para colar em Markdown com checklist técnico por task, owner, artefato, risco e critério de aceite por item**.

[1]: https://docs.streamlit.io/get-started/fundamentals/additional-features?utm_source=chatgpt.com "Additional Streamlit features"
[2]: https://www.enel.com.br/pt/quemsomos/nova-marca.html?utm_source=chatgpt.com "Conheça a nova marca da Enel Brasil"
[3]: https://www.enel.com.br/content/dam/enel-br/documentos-%C3%A9ticos/C%C3%B3digo_de_%C3%89tica.pdf?utm_source=chatgpt.com "Código de Ética"
[4]: https://docs.streamlit.io/develop/api-reference/configuration/config.toml?utm_source=chatgpt.com "config.toml - Streamlit Docs"
