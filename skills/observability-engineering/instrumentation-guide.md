# Instrumentation Guide — OpenTelemetry Code Patterns

## Python (FastAPI)

```python
from opentelemetry import trace, metrics
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

# Auto-instrumentation — always prefer this first
FastAPIInstrumentor.instrument_app(app)

# Custom metric
meter = metrics.get_meter("payment-service")
payment_counter = meter.create_counter(
    "payments_processed_total",
    description="Total payments processed",
    unit="1"
)

# Custom span
tracer = trace.get_tracer("payment-service")

def process_payment(payment_id: str):
    with tracer.start_as_current_span("process_payment") as span:
        span.set_attribute("payment.id", payment_id)
        span.set_attribute("payment.processor", "stripe")
        # business logic
        payment_counter.add(1, {"status": "success", "method": "card"})
```

## Go

```go
import (
    "go.opentelemetry.io/otel"
    "go.opentelemetry.io/otel/attribute"
)

tracer := otel.Tracer("payment-service")

func processPayment(ctx context.Context, paymentID string) error {
    ctx, span := tracer.Start(ctx, "process_payment")
    defer span.End()

    span.SetAttributes(
        attribute.String("payment.id", paymentID),
        attribute.String("payment.processor", "stripe"),
    )
    // business logic
}
```

## OTel Collector — Base Configuration

```yaml
# otel-collector-config.yaml
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317
      http:
        endpoint: 0.0.0.0:4318

processors:
  batch:
    timeout: 1s
    send_batch_size: 1024
  memory_limiter:
    limit_mib: 512
  resource:
    attributes:
      - action: insert
        key: deployment.environment
        value: ${DEPLOYMENT_ENV}

exporters:
  prometheus:
    endpoint: 0.0.0.0:8889
  otlp/tempo:
    endpoint: tempo:4317
    tls:
      insecure: false
  loki:
    endpoint: http://loki:3100/loki/api/v1/push

service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [memory_limiter, batch, resource]
      exporters: [otlp/tempo]
    metrics:
      receivers: [otlp]
      processors: [memory_limiter, batch]
      exporters: [prometheus]
```

## Instrumentation Rules

1. **Auto-instrumentation first** — use OTel agents before manual instrumentation
2. **No instrumentation in hot paths** — high-cardinality metrics in critical loops must use sampling
3. **Metrics for alerts, logs for context** — never use log parsing for alerting
4. **Validate in CI** — instrumentation must be validated in harness (schema check, trace propagation)
5. **Structured logs always** — no `print()` or unstructured `logging.info(f"user {user_id} did X")`
