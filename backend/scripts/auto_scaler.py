import time
import os
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler
from backend.db.redis import get_redis_client, HAS_REDIS

logger = logging.getLogger(__name__)

class MetricsHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/metrics":
            self.send_response(200)
            self.send_header("Content-type", "text/plain")
            self.end_headers()
            
            metrics = []
            if HAS_REDIS:
                try:
                    redis = get_redis_client()
                    
                    # Track Celery / Execution queues lengths
                    # In a real deployed environment, Celery queues might be named 'celery'
                    celery_length = redis.llen("celery")
                    
                    # Track DCN registered nodes count
                    dcn_nodes = redis.hlen("dcn:nodes:registry")
                    
                    metrics.extend([
                        f"# HELP levi_active_dcn_nodes Total number of active registered DCN nodes",
                        f"# TYPE levi_active_dcn_nodes gauge",
                        f"levi_active_dcn_nodes {dcn_nodes}",
                        f"",
                        f"# HELP levi_celery_queue_length Length of the main task queue",
                        f"# TYPE levi_celery_queue_length gauge",
                        f"levi_celery_queue_length {celery_length}"
                    ])
                except Exception as e:
                    logger.error(f"Error fetching metrics: {e}")
            
            self.wfile.write("\n".join(metrics).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

def start_metrics_server(port=8000):
    """
    Sovereign Auto-Scaler Metrics Exporter.
    Exposes metrics for Kubernetes Prometheus Adapter -> HPA.
    """
    server = HTTPServer(("0.0.0.0", port), MetricsHandler)
    print(f"Metrics server running on port {port} for Kubernetes HPA polling...")
    server.serve_forever()

if __name__ == "__main__":
    start_metrics_server()
