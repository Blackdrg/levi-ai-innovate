"""
DEPRECATED — This file is intentionally empty.

The CircuitBreaker class has been consolidated into:
    backend/utils/network.py

That module contains the canonical CircuitBreaker with:
- OPEN / HALF-OPEN / CLOSED states
- async_call() support
- Webhook alert integration (ALERT_WEBHOOK_URL)
- Rate-limit aware (429 does NOT trip the circuit)

Global instances:
    from backend.utils.network import ai_service_breaker, groq_breaker, together_breaker

DO NOT ADD CODE HERE.
"""
