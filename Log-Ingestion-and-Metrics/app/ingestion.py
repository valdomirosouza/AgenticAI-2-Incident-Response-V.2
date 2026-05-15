"""
Pipeline de ingestão de logs HAProxy → Redis.

Estrutura de chaves Redis:
  metrics:requests:total          INCR atômico
  metrics:status:{code}           INCR por status HTTP
  metrics:errors:4xx / 5xx        INCR condicional
  metrics:backend:{name}          INCR por backend
  metrics:frontend:{name}         INCR por frontend
  metrics:response_times          ZADD sorted set (score = ms, member = uuid)
  metrics:rps:{YYYY-MM-DDTHH:MM}  INCR por minuto, janela 60 min
"""

import uuid
import logging
from datetime import datetime, timezone

import redis.asyncio as aioredis

from app.models import HaproxyLog
from app.metrics_registry import HAPROXY_LOGS_INGESTED

logger = logging.getLogger(__name__)

_REDIS_CLIENT: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis:
    global _REDIS_CLIENT
    if _REDIS_CLIENT is None:
        raise RuntimeError("Redis not initialized. Call init_redis() first.")
    return _REDIS_CLIENT


async def init_redis(url: str, password: str = "") -> None:
    global _REDIS_CLIENT
    _REDIS_CLIENT = aioredis.from_url(
        url,
        password=password or None,
        decode_responses=True,
        socket_connect_timeout=5,
    )
    await _REDIS_CLIENT.ping()
    logger.info("Redis connection established")


async def close_redis() -> None:
    global _REDIS_CLIENT
    if _REDIS_CLIENT:
        await _REDIS_CLIENT.aclose()
        _REDIS_CLIENT = None


async def ingest_log(log: HaproxyLog, r: aioredis.Redis) -> None:
    pipe = r.pipeline()

    pipe.incr("metrics:requests:total")
    pipe.incr(f"metrics:status:{log.status_code}")
    pipe.incr(f"metrics:backend:{log.backend}")
    pipe.incr(f"metrics:frontend:{log.frontend}")

    if 400 <= log.status_code < 500:
        pipe.incr("metrics:errors:4xx")
    elif log.status_code >= 500:
        pipe.incr("metrics:errors:5xx")

    # Sorted set com score = latência ms e member único para não colidir
    member = str(uuid.uuid4())
    pipe.zadd("metrics:response_times", {member: log.time_response})

    # RPS por minuto com expiração de 61 minutos
    minute_key = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M")
    rps_key = f"metrics:rps:{minute_key}"
    pipe.incr(rps_key)
    pipe.expire(rps_key, 61 * 60)

    await pipe.execute()

    status_class = f"{log.status_code // 100}xx"
    HAPROXY_LOGS_INGESTED.labels(backend=log.backend, status_class=status_class).inc()

    logger.debug(
        "Log ingested",
        extra={"backend": log.backend, "status_code": log.status_code, "response_ms": log.time_response},
    )
