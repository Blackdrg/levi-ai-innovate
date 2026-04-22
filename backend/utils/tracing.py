"""
Sovereign Distributed Tracing v14.0.
Integrates OpenTelemetry for gateway-to-executor visibility with safe local fallback.
"""

import logging
import os
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Optional

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

logger = logging.getLogger(__name__)

def setup_tracing(app: Optional[Any] = None) -> trace.Tracer:
    """
    Sovereign v14.2.0: OpenTelemetry Tracer Configuration.
    Establishes distributed tracing for high-fidelity cognitive audit.
    """
    service_name = os.getenv("OTEL_SERVICE_NAME", "levi-ai-sovereign")
    otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")

    resource = Resource.create(attributes={
        "service.name": service_name,
        "service.version": "14.2.0",
        "deployment.environment": os.getenv("ENVIRONMENT", "production")
    })

    provider = TracerProvider(resource=resource)
    
    try:
        if not isinstance(trace.get_tracer_provider(), TracerProvider):
            trace.set_tracer_provider(provider)
        
        provider = trace.get_tracer_provider()
        
        zipkin_endpoint = os.getenv("ZIPKIN_ENDPOINT")
        
        if zipkin_endpoint:
            from opentelemetry.exporter.zipkin.json import ZipkinExporter
            zipkin_processor = BatchSpanProcessor(ZipkinExporter(endpoint=zipkin_endpoint))
            provider.add_span_processor(zipkin_processor)
            logger.info("[Tracing] Zipkin exporter initialized: %s", zipkin_endpoint)

        if otlp_endpoint:
            from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
            span_processor = BatchSpanProcessor(OTLPSpanExporter(endpoint=otlp_endpoint))
            provider.add_span_processor(span_processor)
            logger.info("[Tracing] OpenTelemetry initialized. Exporting to %s", otlp_endpoint)
        
        if not zipkin_endpoint and not otlp_endpoint:
            from opentelemetry.sdk.trace.export import ConsoleSpanExporter
            processor = BatchSpanProcessor(ConsoleSpanExporter())
            provider.add_span_processor(processor)
            logger.info("[Tracing] OpenTelemetry initialized with ConsoleExporter (Baseline).")

        if app:
            from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
            FastAPIInstrumentor.instrument_app(app)
            logger.info("[Tracing] FastAPI instrumentation active.")
            
        from opentelemetry.instrumentation.celery import CeleryInstrumentor
        CeleryInstrumentor().instrument()
        logger.info("[Tracing] Celery instrumentation active.")
            
    except Exception as e:
        logger.warning("[Tracing] OTEL init anomaly: %s. Continuing with default tracer.", e)
        
    return trace.get_tracer("levi.sovereign")


# Global Tracer
tracer = trace.get_tracer("levi.sovereign")


@asynccontextmanager
async def traced_span(name: str, **attributes: Any) -> AsyncIterator[Any]:
    """
    Async span helper so the brain and executor can consistently emit spans.
    """
    span = tracer.start_span(name)
    try:
        for key, value in attributes.items():
            if value is not None:
                span.set_attribute(key, value)
        with trace.use_span(span, end_on_exit=False):
            yield span
    except Exception as exc:
        span.record_exception(exc)
        span.set_attribute("error", True)
        raise
    finally:
        span.end()

def set_mission_baggage(mission_id: str):
    """Sets mission_id in OpenTelemetry baggage for cross-boundary propagation."""
    from opentelemetry import baggage, context
    ctx = baggage.set_baggage("mission_id", mission_id)
    return context.attach(ctx)

def get_mission_baggage() -> Optional[str]:
    """Retrieves mission_id from OpenTelemetry baggage."""
    from opentelemetry import baggage
    return baggage.get_baggage("mission_id")
