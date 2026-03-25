# Dimensionamento para Hardware Local

## Especificações da Máquina

| Componente | Especificação |
|---|---|
| CPU | Intel Core i7-1185G7 @ 3.00GHz (4 cores / 8 threads, 11ª geração) |
| RAM | 16GB DDR4 |
| GPU | Intel Iris Xe Graphics (128MB dedicada) — **não utilizável para ML** |
| OS | Linux (kernel 6.17) |

## Estratégia de Alocação de Memória

Com 16GB totais e ~14GB utilizáveis (OS consome ~2GB), a distribuição deve ser criteriosa.

### Perfil "Desenvolvimento" (uso diário)

Apenas os serviços essenciais para desenvolvimento:

| Serviço | RAM Alocada | Notas |
|---|---|---|
| MinIO | 512MB | Single-node, suficiente para dev |
| Spark (local mode) | 4GB | `spark.driver.memory=4g`, sem workers separados |
| Trino | 2GB | `query.max-memory=1GB`, single-worker |
| Airflow (SequentialExecutor) | 1GB | Webserver + Scheduler em processos leves |
| PostgreSQL (metastore) | 512MB | Backend para Airflow + MLflow + Superset |
| FastAPI | 256MB | Uvicorn com 2 workers |
| Nessie | 512MB | Catalog leve |
| **Total Serviços** | **~8.8GB** | |
| **Disponível para ferramentas** | **~5.2GB** | IDE, terminal, browser |

### Perfil "ML Training" (sob demanda)

Para rodar treinamento de modelos, desligar serviços não-essenciais:

| Serviço | RAM Alocada | Notas |
|---|---|---|
| MinIO | 512MB | Precisa para ler dados |
| Spark (local mode) | 2GB | Reduzido para feature engineering |
| MLflow | 512MB | Tracking server |
| PostgreSQL | 512MB | Backend |
| **ML Process** | **6GB** | LightGBM/XGBoost com dados em memória |
| **Total** | **~9.5GB** | |

### Perfil "Full Stack" (demonstração)

Todos os serviços rodando — para demos e testes de integração:

| Serviço | RAM Alocada |
|---|---|
| MinIO | 384MB |
| Spark (local mode) | 2GB |
| Trino | 1.5GB |
| Airflow | 768MB |
| PostgreSQL | 384MB |
| FastAPI | 256MB |
| Nessie | 384MB |
| Superset | 768MB |
| MLflow | 384MB |
| Prometheus | 256MB |
| Grafana | 256MB |
| Great Expectations | 256MB |
| **Total** | **~7.6GB** |

## Docker Compose Profiles

Para gerenciar os perfis de memória, usar Docker Compose profiles:

```yaml
# docker-compose.yml - exemplo de profiles
services:
  minio:
    profiles: ["dev", "ml", "full"]
    deploy:
      resources:
        limits:
          memory: 512M

  spark:
    profiles: ["dev", "ml", "full"]
    # memory ajustada por profile via env vars

  trino:
    profiles: ["dev", "full"]
    # NÃO roda no perfil ML

  superset:
    profiles: ["full"]
    # Só roda no perfil full
```

Comandos:
```bash
# Desenvolvimento diário
docker compose --profile dev up -d

# Treinamento ML
docker compose --profile ml up -d

# Demo/integração
docker compose --profile full up -d
```

## Otimizações para Hardware Limitado

### Spark Local Mode
```python
spark = SparkSession.builder \
    .master("local[4]") \  # 4 cores
    .config("spark.driver.memory", "4g") \
    .config("spark.sql.shuffle.partitions", "8") \  # reduzido de 200
    .config("spark.default.parallelism", "8") \
    .config("spark.sql.adaptive.enabled", "true") \
    .config("spark.sql.adaptive.coalescePartitions.enabled", "true") \
    .getOrCreate()
```

### Trino Single Worker
```properties
# config.properties
coordinator=true
node-scheduler.include-coordinator=true
query.max-memory=1GB
query.max-memory-per-node=1GB
memory.heap-headroom-per-node=0.5GB
```

### Airflow Lightweight
```python
# airflow.cfg
executor = SequentialExecutor  # não LocalExecutor
parallelism = 4
max_active_tasks_per_dag = 2
max_active_runs_per_dag = 1
```

### ML em CPU
- **LightGBM**: `device_type='cpu'`, `num_threads=4`
- **XGBoost**: `tree_method='hist'`, `nthread=4` (hist é o mais eficiente em CPU)
- **scikit-learn**: `n_jobs=4`
- Dados carregados via Polars (mais eficiente que Pandas em memória)

## Limites Operacionais Esperados

| Métrica | Estimativa para 16GB |
|---|---|
| Volume Bronze por carga | Até 2GB por fonte |
| Tabelas Silver simultâneas | 10-15 tabelas |
| Marts Gold | 7-10 marts |
| Registros para ML training | Até ~5M registros (tabulares) |
| Queries Trino concorrentes | 2-3 |
| DAGs Airflow simultâneas | 1-2 |
| Usuários Superset | 1-3 |

## Caminho de Escalabilidade

Quando o volume crescer além do notebook:

1. **Primeiro passo**: Migrar para VM com 32-64GB RAM — mesma arquitetura, só aumentar limites
2. **Segundo passo**: Spark standalone cluster (1 master + N workers) — mudar `master` de `local[*]` para `spark://master:7077`
3. **Terceiro passo**: Kubernetes com Helm charts — cada serviço escala independentemente
4. **Infraestrutura cloud**: MinIO → S3/GCS, Spark → EMR/Dataproc, Trino → Starburst/Athena
