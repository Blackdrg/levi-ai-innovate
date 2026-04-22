import structlog
import logging
import sys
import os

def setup_structured_logging():
    """
    Sovereign Structured Logging v22.1.
    Configures structlog with mission_id context propagation.
    """
    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
        structlog.processors.TimeStamper(fmt="iso"),
    ]

    if os.getenv("ENVIRONMENT") == "production":
        # JSON logs for production (Grafana Loki/ELK compatible)
        processors.append(structlog.processors.JSONRenderer())
    else:
        # Pretty logs for development
        processors.append(structlog.processors.ConsoleRenderer())

    structlog.configure(
        processors=processors,
        logger_factory=structlog.PrintLoggerFactory(),
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        cache_logger_on_first_use=True,
    )

    # Redirect standard logging to structlog
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=logging.INFO,
    )

def get_logger(name: str):
    return structlog.get_logger(name)
