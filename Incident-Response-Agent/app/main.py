from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.auth import require_prometheus_key
from app.config import settings
from app.limiter import limiter
from app.middleware import RequestLoggingMiddleware, RequestSizeLimitMiddleware, SecurityHeadersMiddleware
from app.routers import admin, analyze, health


app = FastAPI(
    title="Incident-Response-Agent",
    version="1.0.0",
    docs_url="/docs" if settings.enable_docs else None,
    redoc_url="/redoc" if settings.enable_docs else None,
    openapi_url="/openapi.json" if settings.enable_docs else None,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)
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
app.include_router(analyze.router)
app.include_router(admin.router)
