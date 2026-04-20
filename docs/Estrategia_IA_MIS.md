# Estratégia de Inteligência Artificial: MIS & Operações (ENEL)
## Visão Executiva para Gerentes de MIS

Este documento detalha os modelos de Inteligência Artificial empregados na nossa plataforma analítica (Data Mesh/Lakehouse local) e as estratégias adotadas para alavancar os dados operacionais (Reclamações, Erros de Leitura, etc.), convertendo texto não estruturado em decisões de negócio ágeis e acionáveis.

---

### 1. Modelos de Inteligência Artificial Utilizados

A arquitetura não depende de APIs comerciais pagas ou serviços em nuvem externa (Vendor Lock-In zero). Utilizamos modelos *open-source* executados localmente em CPU, garantindo privacidade de dados (PII e LGPD) e custo zero por inferência:

- **LLM Principal (Large Language Model):** **Qwen2.5-3B-Instruct-GGUF**
  - **Função:** É o "cérebro" das operações de chat RAG (Retrieval-Augmented Generation) e de *Batch Inference* em pipelines de dados.
  - **Por que usamos:** Sendo um modelo instrucional leve e altamente quantizado, ele é executado inteiramente em processador local (CPU-only) utilizando a biblioteca `llama.cpp`. Ele entende contexto, consolida informações espalhadas e responde com alta acurácia sem onerar custos.

- **Modelo de Embedding (Recuperação RAG):** **all-MiniLM-L6-v2**
  - **Função:** Converte documentos em vetores matemáticos para o banco de dados ChromaDB. Permite realizar "buscas por significado" nas perguntas do usuário.
  - **Por que usamos:** Extremamente rápido e eficiente para mapear a semântica da linguagem humana e parear perguntas executivas com dados do repositório.

- **Modelo de Reranker (Ordenação Fina):** **cross-encoder/ms-marco-MiniLM-L-4-v2**
  - **Função:** Atua como um revisor implacável sobre os resultados da busca (ChromaDB), reorganizando as respostas de modo a trazer os cartões de dados mais relevantes para o topo.
  - **Por que usamos:** Melhora consideravelmente a "precisão do contexto" do agente Chatbot, entregando ao gerente apenas informações pertinentes.

- **Mineração de Tópicos Não Supervisionada (Clustering):** **BERTopic + UMAP + HDBSCAN**
  - **Função:** Lendo textos de milhares de observações em campo simultaneamente, detecta macrotendências, palavras-chave e "esconde-esconde" de motivos de falha de serviço que o SAP não categoriza diretamente.

---

### 2. Estratégia de Implementação (O Valor para o Negócio)

Nossa abordagem de IA é pragmática: foca na **Aceleração da Decisão**. Em vez de tentar "automatizar o trabalho humano" integralmente, a IA entra como um motor de inteligência que alavanca os analistas de dados. 

A implementação está ancorada em **três pilares táticos**:

#### A. Do Sintoma à Causa-Raiz (Pipeline MLOps / Silver)
A diretoria precisava entender as origens de refaturamento. Apenas analisar o "Assunto" nos sistemas clássicos não traz respostas, pois os temas reportados pelos clientes muitas vezes são *sintomas* ("conta muito alta") em vez da *causa real* ("erro de digitação de leiturista"). 
- **O que fazemos:** Injetamos *Regras Determinísticas (Regex)* e uma camada de **LLM Fallback em Lote**. O Qwen2.5 analisa textos com linguagem solta das reclamações do Ceará e converte descrições complexas em uma "Taxonomia Executiva", padronizando a visualização no MIS Aconchegante de forma automatizada e com remoção de dados sensíveis (PII).

#### B. Autonomia Cognitiva com o Agente Chat RAG (Retrieval-Augmented Generation)
Gerentes precisam cruzar informações sobre as praças de São Paulo e Ceará de maneira imediata.
- **O que fazemos:** Implementamos um assistente conversacional dentro do nosso Dashboard MIS (Streamlit). Quando você faz uma pergunta executiva (ex: *"Quais temas dominam as reclamações em CE e cruzam com Erro de Leitura?"*), o sistema:
  1. Detecta a "intenção" e restringe a região.
  2. Aciona o Reranker para recuperar fatos validados e cartões de dados (Datastore).
  3. Gera uma resposta discursiva rica, ancorada EXCLUSIVAMENTE em dados operacionais.

#### C. Governança e Validação (O "LLM Judge" e Roteamento Analítico)
O ambiente não permite falhas de governança (alucinações).
- **O que fazemos:** Implementamos um orquestrador com *Tool Calling* que detecta se uma consulta demanda dados *vivos* ou apenas textuais. Além disso, as interações no Chat RAG são auditadas de forma assíncrona por um "LLM Judge Worker", um modelo IA que lê métricas de telemetria para revisar a Qualidade da Resposta (Precision e Faithfulness). Tudo acontece sem travar a interface visual.

---

### Resumo para a Gestão de MIS
Nossos pipelines não são apenas "transporte de planilhas". Os modelos de Inteligência Artificial transformaram nosso Data Lakehouse local em uma máquina de descoberta semântica, onde o Custo e a Latência foram minimizados usando arquiteturas locais (GGUF, ChromaDB), proporcionando à ENEL autonomia decisória sobre as causas da "Causa Raiz" de ocorrências e erros em massa.