from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from app.auth import require_prometheus_key
from app.config import settings
from app.logging_config import configure_logging
from app.telemetry import configure_telemetry
from app.ingestion import init_redis, close_redis
from app.middleware.request_logging import RequestLoggingMiddleware
from app.middleware.request_size_limit import RequestSizeLimitMiddleware
from app.middleware.security_headers import SecurityHeadersMiddleware
from app.routers import health, logs, metrics


configure_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_redis(settings.redis_url, settings.redis_password)
    yield
    await close_redis()


app = FastAPI(
    title="Log-Ingestion-and-Metrics",
    version="1.0.0",
    docs_url="/docs" if settings.enable_docs else None,
    redoc_url="/redoc" if settings.enable_docs else None,
    openapi_url="/openapi.json" if settings.enable_docs else None,
    lifespan=lifespan,
)

configure_telemetry(app, settings.service_name, settings.otlp_endpoint)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type", "X-API-Key"],
)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(RequestSizeLimitMiddleware)

Instrumentator().instrument(app).expose(
    app,
    endpoint="/prometheus/metrics",
    dependencies=[Depends(require_prometheus_key)],
)

app.include_router(health.router)
app.include_router(logs.router)
app.include_router(metrics.router)
