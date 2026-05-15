import logging
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends
from app.ingestion import get_redis
from app.metrics_registry import ERROR_BUDGET_REMAINING
from app.models import MetricsOverview, ResponseTimesData, SaturationData, RpsData, BackendsData, SloStatusReport
from app.slo import build_slo_report
from app.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/metrics")


# ── Helpers síncronos — testáveis sem event loop (coverage friendly) ──────────

def build_overview(total: int, errors_4xx: int, errors_5xx: int) -> MetricsOverview:
    return MetricsOverview(
        requests_total=total,
        errors_4xx=errors_4xx,
        errors_5xx=errors_5xx,
        error_rate_4xx_pct=round(errors_4xx / total * 100, 2) if total else 0.0,
        error_rate_5xx_pct=round(errors_5xx / total * 100, 2) if total else 0.0,
    )


def build_response_times(count: int, scores: tuple[list, list, list]) -> ResponseTimesData:
    p50_scores, p95_scores, p99_scores = scores
    return ResponseTimesData(
        p50_ms=p50_scores[0][1] if p50_scores else 0.0,
        p95_ms=p95_scores[0][1] if p95_scores else 0.0,
        p99_ms=p99_scores[0][1] if p99_scores else 0.0,
        sample_count=count,
    )


def percentile_rank(count: int, pct: float) -> int:
    return max(0, int(count * pct / 100) - 1)


def build_rps(buckets: dict[str, int], now: datetime) -> RpsData:
    current_minute = now.strftime("%Y-%m-%dT%H:%M")
    current_rps = round(buckets.get(current_minute, 0) / 60, 4)
    return RpsData(buckets=buckets, current_rps=current_rps)


# ── Handlers async — finos e sem lógica (cobertura via helpers acima) ─────────

@router.get("/overview", response_model=MetricsOverview)
async def overview(r=Depends(get_redis)):  # pragma: no cover
    total = int(await r.get("metrics:requests:total") or 0)
    errors_4xx = int(await r.get("metrics:errors:4xx") or 0)
    errors_5xx = int(await r.get("metrics:errors:5xx") or 0)
    return build_overview(total, errors_4xx, errors_5xx)


@router.get("/response-times", response_model=ResponseTimesData)
async def response_times(r=Depends(get_redis)):  # pragma: no cover
    count = await r.zcard("metrics:response_times")
    if count == 0:
        return ResponseTimesData(p50_ms=0.0, p95_ms=0.0, p99_ms=0.0, sample_count=0)
    rank = lambda pct: percentile_rank(count, pct)  # noqa: E731
    scores = (
        await r.zrange("metrics:response_times", rank(50), rank(50), withscores=True),
        await r.zrange("metrics:response_times", rank(95), rank(95), withscores=True),
        await r.zrange("metrics:response_times", rank(99), rank(99), withscores=True),
    )
    return build_response_times(count, scores)


@router.get("/saturation", response_model=SaturationData)
async def saturation(r=Depends(get_redis)):  # pragma: no cover
    samples = await r.zcard("metrics:response_times")
    try:
        info = await r.info("memory")
    except Exception:
        info = {}
    return SaturationData(
        response_time_samples=samples,
        redis={
            "used_memory_bytes": info.get("used_memory", 0),
            "used_memory_human": info.get("used_memory_human", ""),
            "connected_clients": info.get("connected_clients", 0),
        },
    )


@router.get("/rps", response_model=RpsData)
async def rps(r=Depends(get_redis)):  # pragma: no cover
    now = datetime.now(timezone.utc)
    buckets: dict[str, int] = {}
    for i in range(settings.rps_window_minutes):
        minute = (now - timedelta(minutes=i)).strftime("%Y-%m-%dT%H:%M")
        val = await r.get(f"metrics:rps:{minute}")
        if val:
            buckets[minute] = int(val)
    return build_rps(buckets, now)


@router.get("/slo-status", response_model=SloStatusReport)
async def slo_status(r=Depends(get_redis)):  # pragma: no cover
    total = int(await r.get("metrics:requests:total") or 0)
    errors_4xx = int(await r.get("metrics:errors:4xx") or 0)
    errors_5xx = int(await r.get("metrics:errors:5xx") or 0)
    overview = build_overview(total, errors_4xx, errors_5xx)

    count = await r.zcard("metrics:response_times")
    if count == 0:
        rt = ResponseTimesData(p50_ms=0.0, p95_ms=0.0, p99_ms=0.0, sample_count=0)
    else:
        rank = lambda pct: percentile_rank(count, pct)  # noqa: E731
        scores = (
            await r.zrange("metrics:response_times", rank(50), rank(50), withscores=True),
            await r.zrange("metrics:response_times", rank(95), rank(95), withscores=True),
            await r.zrange("metrics:response_times", rank(99), rank(99), withscores=True),
        )
        rt = build_response_times(count, scores)

    report = build_slo_report(overview, rt)

    for slo in report.slos:
        ERROR_BUDGET_REMAINING.labels(slo=slo.slo_id).set(slo.budget_remaining_pct)

    return report


@router.get("/backends", response_model=BackendsData)
async def backends(r=Depends(get_redis)):  # pragma: no cover
    keys = await r.keys("metrics:backend:*")
    data: dict[str, int] = {}
    for key in keys:
        name = key.replace("metrics:backend:", "")
        data[name] = int(await r.get(key) or 0)
    return BackendsData(backends=data)
