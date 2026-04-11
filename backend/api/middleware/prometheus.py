# backend/api/middleware/prometheus.py
import time
from prometheus_client import Counter, Histogram, REGISTRY
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

# Define metrics
REQUEST_COUNT = Counter(
    "leiva_request_count", 
    "Total number of requests received", 
    ["method", "endpoint", "status_code"]
)

REQUEST_LATENCY = Histogram(
    "leiva_request_latency_seconds", 
    "Request latency in seconds", 
    ["method", "endpoint"]
)

MISSION_COST_GAUGE = Counter(
    "leiva_mission_cu_cost_total",
    "Total Compute Units consumed by cognitive missions",
    ["user_id", "tier"]
)

from backend.utils.metrics import MetricsHub, MISSION_CU

class PrometheusMiddleware(BaseHTTPMiddleware):
    """
    Sovereign v14.2.0: High-Fidelity Prometheus Observability.
    Tracks API traffic, cognitive unit consumption, and system health.
    """
    async def dispatch(self, request: Request, call_next):
        if request.url.path == "/metrics":
            return await call_next(request)

        method = request.method
        endpoint = request.url.path
        
        start_time = time.time()
        
        try:
            response = await call_next(request)
            status_code = str(response.status_code)
        except Exception as e:
            status_code = "500"
            raise e
        finally:
            latency = time.time() - start_time
            
            # 1. Update Standard API Metrics
            REQUEST_COUNT.labels(method=method, endpoint=endpoint, status_code=status_code).inc()
            REQUEST_LATENCY.labels(method=method, endpoint=endpoint).observe(latency)
            
            # 2. Trigger System Telemetry Capture
            MetricsHub.capture_system_telemetry()
            
        return response
