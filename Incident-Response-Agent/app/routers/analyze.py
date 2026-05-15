import logging
from fastapi import APIRouter, Depends, Request
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.agents.orchestrator import run_analysis
from app.auth import require_api_key
from app.limiter import limiter
from app.models.report import IncidentReport

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/analyze", response_model=IncidentReport, dependencies=[Depends(require_api_key)])
@limiter.limit("10/minute")
async def analyze(request: Request) -> IncidentReport:
    logger.info("Analysis requested", extra={"path": "/analyze"})
    return await run_analysis()
