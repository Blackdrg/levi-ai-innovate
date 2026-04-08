"""
Sovereign Tracing v8.
Distributed cognitive tracing for the LeviBrain DAG.
"""

import logging
import json
import time
from typing import Dict, Any

from backend.db.redis import r as redis_client, HAS_REDIS
from backend.utils.metrics import MetricsHub
from backend.utils.tracing import tracer

logger = logging.getLogger(__name__)

class CognitiveTracer:
    """
    Tracks the lifecycle of a cognitive mission across the Sovereign OS.
    """

    @staticmethod
    def start_trace(request_id: str, user_id: str, mission_type: str):
        """Initializes a new cognitive trace in the telemetry buffer."""
        span = tracer.start_span(
            "mission.start",
            attributes={
                "mission.request_id": request_id,
                "mission.user_id": user_id,
                "mission.type": mission_type,
            },
        )
        span.end()
        trace_data = {
            "request_id": request_id,
            "user_id": user_id,
            "mission_type": mission_type,
            "start_time": time.time(),
            "steps": []
        }
        if HAS_REDIS:
            redis_client.setex(f"trace:{request_id}", 3600, json.dumps(trace_data))
        logger.info(f"[Tracer] Trace initialized: {request_id}")

    @staticmethod
    def add_step(request_id: str, step_name: str, data: Dict[str, Any]):
        """Records a specific step in the cognitive DAG."""
        if not HAS_REDIS: return
        
        try:
            raw_trace = redis_client.get(f"trace:{request_id}")
            if not raw_trace: return
            
            if isinstance(raw_trace, (bytes, bytearray)):
                raw_trace = raw_trace.decode("utf-8")
            trace = json.loads(raw_trace)
            trace["steps"].append({
                "step": step_name,
                "timestamp": time.time(),
                "data": data
            })
            redis_client.setex(f"trace:{request_id}", 3600, json.dumps(trace))
            MetricsHub.observe_trace_step(step_name, 0)
            span = tracer.start_span(
                f"mission.step.{step_name}",
                attributes={
                    "mission.request_id": request_id,
                    "mission.step": step_name,
                    **{f"mission.data.{k}": v for k, v in data.items() if isinstance(v, (str, int, float, bool))},
                },
            )
            span.end()
        except Exception as e:
            logger.error(f"[Tracer] Step recording failure: {e}")

    @staticmethod
    def end_trace(request_id: str, final_status: str = "success"):
        """Finalizes the trace and triggers long-term telemetry persistence."""
        if not HAS_REDIS: return
        
        try:
            raw_trace = redis_client.get(f"trace:{request_id}")
            if not raw_trace: return
            
            if isinstance(raw_trace, (bytes, bytearray)):
                raw_trace = raw_trace.decode("utf-8")
            trace = json.loads(raw_trace)
            trace["end_time"] = time.time()
            trace["duration"] = trace["end_time"] - trace["start_time"]
            trace["status"] = final_status
            
            redis_client.setex(f"trace:{request_id}", 3600, json.dumps(trace))
            # Store in modern metrics buffer
            redis_client.lpush("metrics:latency_ms", int(trace["duration"] * 1000))
            redis_client.ltrim("metrics:latency_ms", 0, 999)
            MetricsHub.observe_trace_step("mission_total", trace["duration"] * 1000)
            
            # Final trace persistence could go to MongoDB or BigQuery
            logger.info(f"[Tracer] Trace complete: {request_id} | Duration: {trace['duration']:.2f}s")
        except Exception as e:
            logger.error(f"[Tracer] Trace finalization failure: {e}")
