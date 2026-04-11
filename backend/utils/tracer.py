# backend/utils/tracer.py
import os
import logging
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

logger = logging.getLogger(__name__)

def setup_tracer(app=None):
    """
    Sovereign v14.2.0: OpenTelemetry Tracer Configuration.
    Establishes distributed tracing for high-fidelity cognitive audit.
    """
    resource = Resource.create(attributes={
        "service.name": "levi-ai-sovereign",
        "service.version": "14.2.0",
        "deployment.environment": os.getenv("ENVIRONMENT", "production")
    })

    provider = TracerProvider(resource=resource)
    
    # In production, use a real exporter (e.g. OTLP to Cloud Trace)
    # For graduation baseline, we use ConsoleExporter
    processor = BatchSpanProcessor(ConsoleSpanExporter())
    provider.add_span_processor(processor)
    
    trace.set_tracer_provider(provider)
    
    if app:
        FastAPIInstrumentor.instrument_app(app)
        logger.info("[Tracer] FastAPI OTEL instrumentation active.")

def get_tracer():
    return trace.get_tracer("levi.sovereign")
