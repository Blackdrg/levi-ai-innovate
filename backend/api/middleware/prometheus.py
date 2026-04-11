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

class PrometheusMiddleware(BaseHTTPMiddleware):
    """
    Sovereign v14.2.0: Prometheus Observability Middleware.
    Tracks high-fidelity metrics for all cognitive and API traffic.
    """
    async def dispatch(self, request: Request, call_next):
        if request.url.path == "/metrics":
            return await call_next(request)

        method = request.method
        endpoint = request.url.path
        
        start_time = time.time()
        
        response = await call_next(request)
        
        latency = time.time() - start_time
        status_code = str(response.status_code)
        
        # Update metrics
        REQUEST_COUNT.labels(method=method, endpoint=endpoint, status_code=status_code).inc()
        REQUEST_LATENCY.labels(method=method, endpoint=endpoint).observe(latency)
        
        return response
