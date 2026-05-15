import logging
from fastapi import APIRouter, Depends
from app.models import HaproxyLog
from app.ingestion import get_redis, ingest_log

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/logs", status_code=202)
async def ingest(log: HaproxyLog, r=Depends(get_redis)):
    await ingest_log(log, r)
    return {"accepted": True}
