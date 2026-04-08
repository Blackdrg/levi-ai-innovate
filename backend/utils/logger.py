"""
backend/utils/logger.py

Structured JSON Logging configuration for LEVI-AI.
Ensures all logs are machine-readable and include request/user context.
"""

import logging
import sys
import os
from datetime import datetime
from pythonjsonlogger import json
from .logging_context import log_request_id, log_user_id, log_session_id

class LeviJSONFormatter(json.JsonFormatter):
    """
    Custom JSON formatter to inject context variables automatically.
    """
    def add_fields(self, log_record, record, message_dict):
        super(LeviJSONFormatter, self).add_fields(log_record, record, message_dict)
        
        # Inject standard telemetry
        log_record['timestamp'] = datetime.utcnow().isoformat()
        log_record['level'] = record.levelname
        log_record['logger'] = record.name
        
        # Inject Context Variables
        log_record['request_id'] = log_request_id.get()
        log_record['trace_id'] = getattr(record, "trace_id", None) or log_request_id.get()
        log_record['user_id'] = log_user_id.get()
        log_record['session_id'] = getattr(record, "session_id", None) or log_session_id.get()
        log_record['mission_id'] = getattr(record, "mission_id", None)
        log_record['node_id'] = getattr(record, "node_id", None)
        log_record['agent'] = getattr(record, "agent", None)
        log_record['duration_ms'] = getattr(record, "duration_ms", None)
        log_record['status'] = getattr(record, "status", None)

        # Environment metadata
        log_record['env'] = os.getenv("ENVIRONMENT", "development")
        log_record['version'] = "5.0-hardened"

def setup_logging():
    """
    Configures the root logger to use JSON formatting.
    """
    handler = logging.StreamHandler(sys.stdout)
    formatter = LeviJSONFormatter(
        '%(timestamp)s %(level)s %(name)s %(message)s %(request_id)s %(user_id)s'
    )
    handler.setFormatter(formatter)
    
    root = logging.getLogger()
    # Remove existing handlers to avoid double logging
    for h in root.handlers[:]:
        root.removeHandler(h)
        
    root.addHandler(handler)
    root.setLevel(os.getenv("LOG_LEVEL", "INFO"))
    
    # Silence verbose secondary libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("azure").setLevel(logging.WARNING)
    logging.getLogger("google").setLevel(logging.WARNING)

    logging.info("Structured Logging: Activated.")

def get_logger(name: str):
    """ Returns a logger instance for the given name. """
    return logging.getLogger(name)
