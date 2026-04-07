"""
Sovereign Distributed Tracing v14.0.
Integrates OpenTelemetry and Jaeger for full-stack request visibility.
Captures spans for Agents, DB queries, and DCN gossip pulses.
"""

import os
import logging
from typing import Optional
from opentelemetry import trace
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

logger = logging.getLogger(__name__)

def setup_tracing(app: Optional[Any] = None) -> trace.Tracer:
    """Configures the global TracerProvider and instruments the FastAPI app."""
    service_name = os.getenv("OTEL_SERVICE_NAME", "levi-backend")
    jaeger_host = os.getenv("JAEGER_HOST", "localhost")
    jaeger_port = int(os.getenv("JAEGER_PORT", "6831"))

    resource = Resource(attributes={
        SERVICE_NAME: service_name,
        "version": "v14.0.0-Autonomous"
    })

    provider = TracerProvider(resource=resource)
    
    try:
        jaeger_exporter = JaegerExporter(
            agent_host_name=jaeger_host,
            agent_port=jaeger_port,
        )
        span_processor = BatchSpanProcessor(jaeger_exporter)
        provider.add_span_processor(span_processor)
        
        trace.set_tracer_provider(provider)
        logger.info(f"[Tracing] OpenTelemetry initialized. Exporting to {jaeger_host}:{jaeger_port}")
        
        if app:
            FastAPIInstrumentor.instrument_app(app)
            logger.info("[Tracing] FastAPI instrumentation active.")
            
    except Exception as e:
        logger.warning(f"[Tracing] Failed to initialize Jaeger exporter: {e}. Defaulting to NoOpTracer.")
        
    return trace.get_tracer(__name__)

# Global Tracer
tracer = trace.get_tracer("levi.sovereign")
