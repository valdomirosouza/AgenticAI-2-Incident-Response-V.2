"""
Load tests — S4-03: Validação de SLOs sob carga (SDD §8).

Uso headless (ingestion only, 100 usuários, 60s):
  locust -f load-tests/locustfile.py \
    --host http://localhost:8000 \
    --users 100 --spawn-rate 10 \
    --run-time 60s --headless \
    --csv load-tests/results/ingest

Uso com UI (ambos os serviços):
  ANALYSIS_HOST=http://localhost:8001 ANALYSIS_API_KEY=<key> \
  locust -f load-tests/locustfile.py --host http://localhost:8000

Variáveis de ambiente:
  ANALYSIS_HOST      — URL do Incident-Response-Agent (default: http://localhost:8001)
  ANALYSIS_API_KEY   — API key do IRA (default: "")
"""

import os
import random
from locust import HttpUser, task, between, constant_throughput

ANALYSIS_HOST = os.environ.get("ANALYSIS_HOST", "http://localhost:8001")
ANALYSIS_API_KEY = os.environ.get("ANALYSIS_API_KEY", "")

SAMPLE_BACKENDS = ["web-backend", "api-backend", "static-backend"]
SAMPLE_FRONTENDS = ["http-in", "https-in"]
SAMPLE_STATUS_CODES = [200, 200, 200, 200, 200, 404, 500, 503]


def _random_log() -> dict:
    return {
        "frontend": random.choice(SAMPLE_FRONTENDS),
        "backend": random.choice(SAMPLE_BACKENDS),
        "status_code": random.choice(SAMPLE_STATUS_CODES),
        "time_response": random.uniform(10, 800),
        "bytes_read": random.randint(512, 65536),
        "request_method": random.choice(["GET", "POST", "PUT"]),
        "request_path": random.choice(["/api/v1/data", "/health", "/metrics"]),
    }


class LogIngestionUser(HttpUser):
    """
    Simula ingestão de logs HAProxy + leitura de métricas.
    SLO: P95 < 100ms para POST /logs, taxa 5xx < 1%.
    Escalar com --users 100 --spawn-rate 10 para atingir ~100 RPS.
    Host: controlado por --host (default: http://localhost:8000).
    """

    wait_time = constant_throughput(1)  # 1 req/s por usuário

    @task(10)
    def ingest_log(self):
        with self.client.post(
            "/logs",
            json=_random_log(),
            name="POST /logs",
            catch_response=True,
        ) as resp:
            if resp.status_code == 202:
                resp.success()
            elif resp.status_code >= 500:
                resp.failure(f"5xx server error: {resp.status_code}")
            # 422 é falha de validação — marcado como falha para detectar regressão
            elif resp.status_code == 422:
                resp.failure("422 Unprocessable Entity — payload inválido")

    @task(2)
    def get_overview(self):
        self.client.get("/metrics/overview", name="GET /metrics/overview")

    @task(1)
    def get_response_times(self):
        self.client.get("/metrics/response-times", name="GET /metrics/response-times")

    @task(1)
    def get_health(self):
        with self.client.get("/health", name="GET /health", catch_response=True) as resp:
            if resp.json().get("status") != "ok":
                resp.failure("health degraded")


class AnalysisUser(HttpUser):
    """
    Simula chamadas ao endpoint de análise do Incident-Response-Agent.
    SLO: P95 < 30s. Rate limit do serviço: 10 requisições/minuto por IP.
    Usar com 1 usuário para respeitar o rate limit.

    Host: configurado por ANALYSIS_HOST (não usa --host para não colidir com LogIngestionUser).
    """

    host = ANALYSIS_HOST
    wait_time = between(6, 10)  # ~7 RPM médio — abaixo do limite de 10/min

    @task
    def analyze(self):
        headers = {"X-API-Key": ANALYSIS_API_KEY} if ANALYSIS_API_KEY else {}
        with self.client.post(
            "/analyze",
            headers=headers,
            name="POST /analyze",
            timeout=60,
            catch_response=True,
        ) as resp:
            if resp.status_code == 200:
                resp.success()
            elif resp.status_code == 429:
                # Rate limit atingido — comportamento esperado, não é falha de SLO
                resp.success()
            elif resp.status_code == 401:
                resp.failure("401 Unauthorized — verificar ANALYSIS_API_KEY")
            else:
                resp.failure(f"unexpected status: {resp.status_code}")
