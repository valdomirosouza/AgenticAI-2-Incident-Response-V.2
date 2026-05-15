import sys
import logging
from fastapi import FastAPI

logger = logging.getLogger(__name__)


def configure_telemetry(app: FastAPI, service_name: str, otlp_endpoint: str = "") -> None:
    # Não inicializa em ambiente de testes
    if "pytest" in sys.modules:
        return

    try:
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.instrumentation.redis import RedisInstrumentor

        resource = Resource.create({"service.name": service_name})
        provider = TracerProvider(resource=resource)

        if otlp_endpoint:
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

            provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=otlp_endpoint)))
        else:
            from opentelemetry.sdk.trace.export import ConsoleSpanExporter

            provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))

        trace.set_tracer_provider(provider)
        FastAPIInstrumentor.instrument_app(app)
        RedisInstrumentor().instrument()
        logger.info("OpenTelemetry configured", extra={"service": service_name})

    except Exception as exc:
        logger.warning("Failed to configure OpenTelemetry: %s", exc)
