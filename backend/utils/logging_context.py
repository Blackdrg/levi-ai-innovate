from contextvars import ContextVar

# Context variables for logging
log_request_id: ContextVar[str] = ContextVar("log_request_id", default="none")
log_user_id: ContextVar[str] = ContextVar("log_user_id", default="none")
