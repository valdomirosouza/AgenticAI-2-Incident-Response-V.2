# Resilience Patterns — Code Reference

## Retry with Exponential Backoff + Jitter (Python)

```python
import random, time

def retry_with_backoff(func, max_retries=3, base_delay=0.1, max_delay=30.0):
    """
    Retry with exponential backoff and jitter.
    Jitter (±25%) prevents retry storms when multiple clients fail simultaneously.
    """
    for attempt in range(max_retries):
        try:
            return func()
        except TransientError as e:
            if attempt == max_retries - 1:
                raise
            delay = min(base_delay * (2 ** attempt), max_delay)
            jitter = delay * 0.25 * random.uniform(-1, 1)
            time.sleep(delay + jitter)
```

## Circuit Breaker (Python)

```python
from enum import Enum
from datetime import datetime, timedelta
import threading

class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

class CircuitBreaker:
    def __init__(self, failure_threshold=5, recovery_timeout=60, probe_success_threshold=2):
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.probe_success_threshold = probe_success_threshold
        self.last_failure_time = None
        self.probe_successes = 0
        self._lock = threading.Lock()

    def call(self, func, *args, **kwargs):
        with self._lock:
            if self.state == CircuitState.OPEN:
                if datetime.now() - self.last_failure_time > timedelta(seconds=self.recovery_timeout):
                    self.state = CircuitState.HALF_OPEN
                    self.probe_successes = 0
                else:
                    raise CircuitOpenError("Circuit breaker is OPEN — fast failing")

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise

    def _on_success(self):
        with self._lock:
            if self.state == CircuitState.HALF_OPEN:
                self.probe_successes += 1
                if self.probe_successes >= self.probe_success_threshold:
                    self.state = CircuitState.CLOSED
                    self.failure_count = 0
            elif self.state == CircuitState.CLOSED:
                self.failure_count = 0

    def _on_failure(self):
        with self._lock:
            self.failure_count += 1
            self.last_failure_time = datetime.now()
            if self.failure_count >= self.failure_threshold:
                self.state = CircuitState.OPEN
```

## Kubernetes Probes — Liveness vs Readiness

```yaml
# CORRECT: separated probes with different semantics
livenessProbe:
  httpGet:
    path: /health/live     # Only checks: is the process alive?
    port: 8080
  initialDelaySeconds: 10
  periodSeconds: 10
  failureThreshold: 3       # Restart container after 3 consecutive failures

readinessProbe:
  httpGet:
    path: /health/ready    # Checks: DB, cache, critical dependencies
    port: 8080
  initialDelaySeconds: 5
  periodSeconds: 5
  failureThreshold: 3       # Remove from load balancer after 3 consecutive failures
```

```python
# Health endpoint implementation
@app.get("/health/live")
def liveness():
    """Only checks if the process is functional — no external deps."""
    return {"status": "ok"}

@app.get("/health/ready")
def readiness():
    """Checks all critical dependencies."""
    checks = {}
    try:
        db.execute("SELECT 1")
        checks["database"] = "ok"
    except Exception as e:
        checks["database"] = f"error: {e}"

    try:
        redis_client.ping()
        checks["cache"] = "ok"
    except Exception as e:
        checks["cache"] = f"error: {e}"

    all_ok = all(v == "ok" for v in checks.values())
    status_code = 200 if all_ok else 503
    return JSONResponse({"status": "ready" if all_ok else "not_ready", "checks": checks}, status_code=status_code)
```

## Cache Stampede Prevention (Python)

```python
import time, random, threading

_rebuild_locks = {}
_locks_lock = threading.Lock()

def get_with_stampede_protection(cache, key, rebuild_fn, ttl=300):
    """
    Prevents cache stampede: only one caller rebuilds the cache.
    Others wait briefly, then serve stale if available.
    """
    value = cache.get(key)
    if value is not None:
        return value

    with _locks_lock:
        if key not in _rebuild_locks:
            _rebuild_locks[key] = threading.Lock()
        lock = _rebuild_locks[key]

    if lock.acquire(timeout=2.0):  # Wait max 2s for rebuild
        try:
            value = cache.get(key)  # Re-check after acquiring lock
            if value is None:
                value = rebuild_fn()
                ttl_with_jitter = ttl + random.randint(-30, 30)  # Stagger expiry
                cache.set(key, value, ex=ttl_with_jitter)
            return value
        finally:
            lock.release()
    else:
        # Could not acquire lock — return stale or empty
        return cache.get(f"{key}:stale") or rebuild_fn()
```
