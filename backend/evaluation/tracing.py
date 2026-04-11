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

import re

class CognitiveTracer:
    """
    Tracks the lifecycle of a cognitive mission across the Sovereign OS.
    Features: GDPR-compliant PII Scrubber & HMAC Integrity.
    """
    
    # GDPR Baseline Patterns
    PII_PATTERNS = {
        "email": r"[\w\.-]+@[\w\.-]+\.\w+",
        "ssn": r"\b\d{3}-\d{2}-\d{4}\b",
        "credit_card": r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b",
        "phone": r"\b\d{3}[-\s]?\d{3}[-\s]?\d{4}\b",
        "ipv4": r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b",
    }
    
    # HIPAA Extension Patterns (Optional/Configurable)
    HIPAA_PATTERNS = {
        "medical_record_number": r"\bMRN\d{6,}\b",
        "health_plan_id": r"\bHPID\d{6,}\b",
    }

    @staticmethod
    def _scrub_pii(data: Any, strict: bool = True, hipaa: bool = False) -> Any:
        """Neutralizes PII in strings and nested structures."""
        patterns = {**CognitiveTracer.PII_PATTERNS}
        if hipaa:
            patterns.update(CognitiveTracer.HIPAA_PATTERNS)
            
        if isinstance(data, str):
            scrubbed = data
            for label, pattern in patterns.items():
                scrubbed = re.sub(pattern, f"[REDACTED_{label.upper()}]", scrubbed)
            return scrubbed
        elif isinstance(data, dict):
            return {k: CognitiveTracer._scrub_pii(v, strict, hipaa) for k, v in data.items()}
        elif isinstance(data, list):
            return [CognitiveTracer._scrub_pii(i, strict, hipaa) for i in data]
        return data

    @staticmethod
    def start_trace(request_id: str, user_id: str, mission_type: str):
        """Initializes a new cognitive trace in the telemetry buffer."""
        # Config check for HIPAA
        use_hipaa = os.getenv("SOVEREIGN_HIPAA_MODE", "false").lower() == "true"
        
        # 🛡️ Graduation #11: Start OTEL Root Span
        span = tracer.start_span(
            f"mission:{mission_type}",
            attributes={
                "mission.request_id": request_id,
                "mission.user_id": CognitiveTracer._scrub_pii(user_id),
                "mission.type": mission_type,
                "sovereign.version": "14.2.0"
            },
        )
        # Store span reference if needed, but for now we follow the trace context
        
        trace_data = {
            "request_id": request_id,
            "user_id": user_id, 
            "mission_type": mission_type,
            "start_time": time.time(),
            "steps": [],
            "hipaa_active": use_hipaa,
            "otel_trace_id": format(span.get_span_context().trace_id, '032x')
        }
        if HAS_REDIS:
            redis_client.setex(f"trace:{request_id}", 3600, json.dumps(trace_data))
        
        # We end the start span quickly as we'll have sub-spans for steps
        span.end()
        logger.info(f"[Tracer] Trace initialized: {request_id}")

    @staticmethod
    def add_step(request_id: str, step_name: str, data: Dict[str, Any]):
        """Records a specific step in the cognitive DAG with PII scrubbing."""
        if not HAS_REDIS: return
        
        try:
            raw_trace = redis_client.get(f"trace:{request_id}")
            if not raw_trace: return
            
            if isinstance(raw_trace, (bytes, bytearray)):
                raw_trace = raw_trace.decode("utf-8")
            trace_obj = json.loads(raw_trace)
            
            # Application of PII Neutralization logic
            use_hipaa = trace_obj.get("hipaa_active", False)
            scrubbed_data = CognitiveTracer._scrub_pii(data, hipaa=use_hipaa)
            
            trace_obj["steps"].append({
                "step": step_name,
                "timestamp": time.time(),
                "data": scrubbed_data
            })
            redis_client.setex(f"trace:{request_id}", 3600, json.dumps(trace_obj))
            MetricsHub.observe_trace_step(step_name, 0)
            
            # 🛡️ Graduation #11: OTEL Step Span with context linkage
            # Note: In a production async env, we'd use set_span_in_context
            with tracer.start_as_current_span(f"step:{step_name}") as span:
                span_attrs = {
                    "mission.request_id": request_id,
                    "mission.step": step_name,
                }
                for k, v in scrubbed_data.items():
                    if isinstance(v, (str, int, float, bool)):
                        span_attrs[f"mission.data.{k}"] = v
                span.set_attributes(span_attrs)
                
        except Exception as e:
            logger.error(f"[Tracer] Step recording failure: {e}")

    @staticmethod
    def end_trace(request_id: str, final_status: str = "success"):
        """Finalizes the trace and implements HMAC-based Audit Integrity."""
        if not HAS_REDIS: return
        
        try:
            raw_trace = redis_client.get(f"trace:{request_id}")
            if not raw_trace: return
            
            if isinstance(raw_trace, (bytes, bytearray)):
                raw_trace = raw_trace.decode("utf-8")
            trace_obj = json.loads(raw_trace)
            trace_obj["end_time"] = time.time()
            trace_obj["duration"] = trace_obj["end_time"] - trace_obj["start_time"]
            trace_obj["status"] = final_status
            
            # --- HMAC Audit Chain Phase ---
            from backend.utils.encryption import SovereignKMS
            # Sign the entire trace block for forensic compliance
            trace_payload = json.dumps(trace_obj, sort_keys=True)
            trace_obj["integrity_hmac"] = SovereignKMS.sign_trace(trace_payload)
            
            redis_client.setex(f"trace:{request_id}", 3600, json.dumps(trace_obj))
            
            # Store in metrics buffer
            redis_client.lpush("metrics:latency_ms", int(trace_obj["duration"] * 1000))
            redis_client.ltrim("metrics:latency_ms", 0, 999)
            MetricsHub.observe_trace_step("mission_total", trace_obj["duration"] * 1000)
            
            logger.info(f"[Tracer] Trace complete: {request_id} | Integrity Signed: {trace_obj['integrity_hmac'][:16]}...")
        except Exception as e:
            logger.error(f"[Tracer] Trace finalization failure: {e}")
