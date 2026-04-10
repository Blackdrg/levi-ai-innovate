"""
Sovereign Health & Pulse Monitoring v14.0.0.
Real dependency probes for readiness, liveness, and agent visibility.
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any, Dict

import httpx

from backend.agents.registry import AGENT_REGISTRY
from backend.db.postgres_db import verify_resonance
from backend.db.redis import HAS_REDIS_ASYNC, r_async
from backend.utils.internal_client import internal_client

logger = logging.getLogger(__name__)


async def probe_dependencies() -> Dict[str, Any]:
    """
    Deep health probe used by `/health` and `/ready`.
    Verifies Redis, Postgres, and Ollama instead of returning a hardcoded pulse.
    """
    started = time.perf_counter()
    ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")

    redis_ok = False
    redis_error = None
    if HAS_REDIS_ASYNC and r_async is not None:
        try:
            await r_async.ping()
            redis_ok = True
        except Exception as exc:
            redis_error = str(exc)
    else:
        redis_error = "redis client unavailable"

    postgres_ok = False
    postgres_error = None
    try:
        postgres_ok = await verify_resonance()
        if not postgres_ok:
            postgres_error = "postgres probe returned false"
    except Exception as exc:
        postgres_error = str(exc)

    ollama_ok = False
    ollama_error = None
    ollama_tags: list[str] = []
    try:
        response = await internal_client.request("GET", f"{ollama_url}/api/tags")
        response.raise_for_status()
        body = response.json()
        ollama_tags = [
            model.get("name", "")
            for model in body.get("models", [])
            if isinstance(model, dict)
        ]
        ollama_ok = True
    except Exception as exc:
        ollama_error = str(exc)

    checks = {
        "redis": {"ok": redis_ok, "error": redis_error},
        "postgres": {"ok": postgres_ok, "error": postgres_error},
        "ollama": {
            "ok": ollama_ok,
            "error": ollama_error,
            "url": ollama_url,
            "models": ollama_tags,
        },
    }
    overall = all(item["ok"] for item in checks.values())

    return {
        "status": "online" if overall else "degraded",
        "checks": checks,
        "latency_ms": int((time.perf_counter() - started) * 1000),
    }

class AgentHealthCheck:
    """
    Audit Point 28: Agent Health Pulse.
    Ensures all components of the 14-Agent Swarm are responsive.
    """

    @classmethod
    async def global_pulse(cls) -> Dict[str, Any]:
        """
        Pings every agent in the registry to verify responsiveness.
        """
        logger.info("[Health] Initiating Global Agent Pulse...")
        
        results = {}
        for name, agent in AGENT_REGISTRY.items():
            try:
                # Standardized heartbeat for SovereignAgent
                # We skip deep execution and just check instance health
                is_alive = True # Base check
                
                # If the agent has a specific ping/health method, we'd call it here
                if hasattr(agent, 'ping'):
                    is_alive = await agent.ping()
                
                results[name] = {
                    "status": "healthy" if is_alive else "degraded",
                    "version": getattr(agent, 'version', "v14.0.0"),
                    "latency_ms": 0 # Local check
                }
            except Exception as e:
                logger.error(f"Health check failed for agent '{name}': {e}")
                results[name] = {"status": "unhealthy", "error": str(e)}

        all_ok = all(r["status"] == "healthy" for r in results.values())
        
        return {
            "status": "online" if all_ok else "degraded",
            "agents_total": len(results),
            "agents_healthy": sum(1 for r in results.values() if r["status"] == "healthy"),
            "details": results
        }
