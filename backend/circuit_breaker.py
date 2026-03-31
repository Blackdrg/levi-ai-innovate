"""
backend/circuit_breaker.py

PROXY MODULE — Re-exports CircuitBreaker instances from backend.utils.network.
This maintains compatibility with legacy v5.0 code during the v6.8 transition.
"""

from backend.utils.network import (
    CircuitBreaker,
    ai_service_breaker,
    groq_breaker,
    together_breaker
)

# Canonical instances are now managed in backend.utils.network.
# We export them here to fix ModuleNotFoundError in old tests and services.
__all__ = [
    "CircuitBreaker",
    "ai_service_breaker",
    "groq_breaker",
    "together_breaker"
]
