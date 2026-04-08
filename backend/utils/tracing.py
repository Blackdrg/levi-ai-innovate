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
    """Configures the global TracerProvider and instruments the FastAPI app."""
    service_name = os.getenv("OTEL_SERVICE_NAME", "levi-backend")
    otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")

    resource = Resource(attributes={
        SERVICE_NAME: service_name,
        "version": "v14.0.0-Autonomous"
    })

    provider = TracerProvider(resource=resource)
    
    try:
        if not isinstance(trace.get_tracer_provider(), TracerProvider):
            trace.set_tracer_provider(provider)
        provider = trace.get_tracer_provider()
        if otlp_endpoint:
            span_processor = BatchSpanProcessor(OTLPSpanExporter(endpoint=otlp_endpoint))
            provider.add_span_processor(span_processor)
            logger.info("[Tracing] OpenTelemetry initialized. Exporting to %s", otlp_endpoint)
        else:
            logger.info("[Tracing] OpenTelemetry initialized without remote exporter.")

        if app:
            FastAPIInstrumentor.instrument_app(app)
            logger.info("[Tracing] FastAPI instrumentation active.")
            
    except Exception as e:
        logger.warning("[Tracing] Failed to initialize OTLP exporter: %s. Defaulting to local tracer.", e)
        
    return trace.get_tracer(__name__)

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
