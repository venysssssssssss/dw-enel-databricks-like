from __future__ import annotations

from httpx import ASGITransport, AsyncClient
import pytest
import pytest_asyncio

from src.api.auth.jwt import create_access_token
from src.api.infrastructure.trino_client import InMemoryTrinoClient
from src.api.main import create_app


@pytest_asyncio.fixture
async def client():
    app = create_app(
        enable_lifespan=False,
        enable_rate_limit=False,
        enable_observability=False,
        enable_middlewares=False,
    )
    app.state.trino = InMemoryTrinoClient(
        fixtures={
            "select 0 as total_notas, 0.0 as efetividade_bruta_pct, 0.0 as efetividade_liquida_pct, 0.0 as taxa_devolucao_pct": [
                {
                    "total_notas": 0,
                    "efetividade_bruta_pct": 0.0,
                    "efetividade_liquida_pct": 0.0,
                    "taxa_devolucao_pct": 0.0,
                }
            ],
            "select * from gold.score_atraso_entrega where score_atraso >= 0.0 order by score_atraso desc limit 50 offset 0": [
                {
                    "cod_nota": 1,
                    "score_atraso": 0.81,
                    "classe_predita": "ALTO_RISCO",
                    "dias_atraso_pred": 3.0,
                    "model_version": "20260325010101",
                    "data_scoring": "2026-03-25",
                }
            ],
            "select * from gold.score_atraso_entrega where cod_nota = 1": [
                {
                    "cod_nota": 1,
                    "score_atraso": 0.81,
                    "classe_predita": "ALTO_RISCO",
                    "dias_atraso_pred": 3.0,
                    "model_version": "20260325010101",
                    "data_scoring": "2026-03-25",
                    "explanations": (
                        '[{"feature_name":"dias_ate_vencimento","shap_value":2.0,'
                        '"direction":"AUMENTA_RISCO"}]'
                    ),
                }
            ],
            "select * from gold.score_inadimplencia where score_inadimplencia >= 0.0 order by score_inadimplencia desc limit 50 offset 0": [
                {
                    "cod_fatura": 10,
                    "score_inadimplencia": 0.62,
                    "segmento_risco": "ALTO",
                }
            ],
            "select * from gold.score_metas where projecao_pct >= 0.0 order by projecao_pct desc limit 50 offset 0": [
                {
                    "cod_base": 20,
                    "projecao_pct": 93.0,
                    "flag_risco": False,
                }
            ],
            "select * from gold.score_anomalias where anomaly_score >= 0.0 order by anomaly_score desc limit 50 offset 0": [
                {
                    "entidade_id": "base-1",
                    "anomaly_score": 0.74,
                    "is_anomaly": True,
                }
            ],
            "select topic_id, topic_name, quantidade, percentual from gold.vw_erro_leitura_padroes  order by quantidade desc": [
                {
                    "topic_id": 1,
                    "topic_name": "leitura_estimada",
                    "quantidade": 10,
                    "percentual": 50.0,
                }
            ],
            "select regiao, classe_erro, data, qtd_erros, anomaly_score, is_anomaly from gold.hotspots_erro_leitura where regiao = 'CE' order by anomaly_score desc": [
                {
                    "regiao": "CE",
                    "classe_erro": "leitura_estimada",
                    "data": "2026-01-01",
                    "qtd_erros": 5,
                    "anomaly_score": 0.91,
                    "is_anomaly": True,
                }
            ],
            "select * from gold.fato_erro_leitura where ordem = '123'": [
                {
                    "ordem": "123",
                    "classe": "leitura_estimada",
                    "probabilidade": 0.8,
                    "causa_raiz": "LEITURA_ESTIMADA",
                    "status": "ENCERRADA",
                    "regiao": "CE",
                    "explicacao": ["token: estimada"],
                }
            ],
        },
    )
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as async_client:
        yield async_client


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient) -> None:
    response = await client.get("/api/v1/health/")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_export_requires_auth(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/exports/notas",
        json={"periodo_inicio": "2026-01-01", "periodo_fim": "2026-01-31"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_metrics_authenticated(client: AsyncClient) -> None:
    token = create_access_token({"sub": "admin", "role": "admin"})
    response = await client.get(
        "/api/v1/metrics/efetividade",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json()["total_notas"] == 0


@pytest.mark.asyncio
async def test_scores_endpoints_authenticated(client: AsyncClient) -> None:
    token = create_access_token({"sub": "admin", "role": "admin"})
    headers = {"Authorization": f"Bearer {token}"}

    atraso = await client.get("/api/v1/scores/atraso", headers=headers)
    inadimplencia = await client.get("/api/v1/scores/inadimplencia", headers=headers)
    metas = await client.get("/api/v1/scores/metas", headers=headers)
    anomalias = await client.get("/api/v1/scores/anomalias", headers=headers)

    assert atraso.status_code == 200
    assert atraso.json()["data"][0]["score_atraso"] == 0.81
    assert inadimplencia.status_code == 200
    assert inadimplencia.json()["data"][0]["segmento_risco"] == "ALTO"
    assert metas.status_code == 200
    assert metas.json()["data"][0]["projecao_pct"] == 93.0
    assert anomalias.status_code == 200
    assert anomalias.json()["data"][0]["is_anomaly"] is True


@pytest.mark.asyncio
async def test_score_detail_returns_explanations(client: AsyncClient) -> None:
    token = create_access_token({"sub": "admin", "role": "admin"})
    response = await client.get(
        "/api/v1/scores/atraso/1",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["cod_nota"] == 1
    assert payload["explanations"][0]["feature_name"] == "dias_ate_vencimento"


@pytest.mark.asyncio
async def test_validation_error_returns_422(client: AsyncClient) -> None:
    token = create_access_token({"sub": "admin", "role": "admin"})
    response = await client.get(
        "/api/v1/scores/atraso",
        params={"min_score": 5},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_erro_leitura_endpoints_authenticated(client: AsyncClient) -> None:
    token = create_access_token({"sub": "admin", "role": "admin"})
    headers = {"Authorization": f"Bearer {token}"}

    classification = await client.post(
        "/api/v1/erros-leitura/classificar",
        json={"texto": "Cliente informa leitura estimada ha tres meses"},
        headers=headers,
    )
    padroes = await client.get("/api/v1/erros-leitura/padroes", headers=headers)
    hotspots = await client.get("/api/v1/erros-leitura/hotspots", params={"regiao": "CE"}, headers=headers)
    ordem = await client.get("/api/v1/erros-leitura/123", headers=headers)

    assert classification.status_code == 200
    assert classification.json()["classe"] == "leitura_estimada"
    assert padroes.status_code == 200
    assert padroes.json()[0]["topic_name"] == "leitura_estimada"
    assert hotspots.status_code == 200
    assert hotspots.json()[0]["is_anomaly"] is True
    assert ordem.status_code == 200
    assert ordem.json()["ordem"] == "123"
