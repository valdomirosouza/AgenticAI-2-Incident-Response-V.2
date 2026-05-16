from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.middleware import RequestLoggingMiddleware, RequestSizeLimitMiddleware, SecurityHeadersMiddleware
from app.routers import health, kb
from app.services.qdrant_service import ensure_collection


@asynccontextmanager
async def lifespan(app: FastAPI):
    await ensure_collection()
    yield


app = FastAPI(
    title="Knowledge-Base",
    version="1.0.0",
    docs_url="/docs" if settings.enable_docs else None,
    redoc_url="/redoc" if settings.enable_docs else None,
    openapi_url="/openapi.json" if settings.enable_docs else None,
    lifespan=lifespan,
)

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

app.include_router(health.router)
app.include_router(kb.router)
