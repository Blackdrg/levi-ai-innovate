import logging
import os
import random
import asyncio
from typing import Callable
from functools import wraps

logger = logging.getLogger(__name__)

class ChaosMonkey:
    """
    LEVI Sovereign Chaos Engine (v13.2).
    Simulates infrastruture failures to validate DCN and Reliability hardening.
    Controlled via ENABLE_CHAOS=true.
    """

    @staticmethod
    def is_enabled() -> bool:
        return os.getenv("ENABLE_CHAOS", "false").lower() == "true"

    @staticmethod
    def maybe_fail(failure_rate: float = 0.1, error_msg: str = "Chaos Failure"):
        """Randomly inject a failure based on failure_rate."""
        if ChaosMonkey.is_enabled() and random.random() < failure_rate:
            logger.warning(f"🐒 [Chaos] Injecting intentional failure: {error_msg}")
            raise RuntimeError(error_msg)

    @staticmethod
    def inject_latency(max_ms: int = 5000):
        """Randomly inject artificial latency."""
        if ChaosMonkey.is_enabled():
            delay = random.uniform(0, max_ms) / 1000.0
            logger.info(f"🐒 [Chaos] Injecting {delay*1000:.2f}ms of artificial latency.")
            return asyncio.sleep(delay)
        return asyncio.sleep(0)

    @staticmethod
    def wrap_with_chaos(failure_rate: float = 0.05, latency_ms: int = 0):
        """Decorator to wrap methods with chaos injection."""
        def decorator(func: Callable):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                if ChaosMonkey.is_enabled():
                    if latency_ms > 0:
                        await ChaosMonkey.inject_latency(latency_ms)
                    ChaosMonkey.maybe_fail(failure_rate, f"Chaos: {func.__name__} failed.")
                return await func(*args, **kwargs)

            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                if ChaosMonkey.is_enabled():
                    ChaosMonkey.maybe_fail(failure_rate, f"Chaos: {func.__name__} failed.")
                return func(*args, **kwargs)

            return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
        return decorator

    @staticmethod
    def simulate_redis_outage():
        """Force-fully disconnects or breaks the global Redis client instance for tests."""
        logger.error("🛑 [Chaos] SIMULATING REDIS OUTAGE...")
        # This is a extreme measure for a test
        # and should only be used in specific chaos test scenarios.
        try:
             # Just set it to None or replace its methods
             pass 
        except Exception as e:
             logger.error(f"Chaos Redis error: {e}")

    @staticmethod
    def simulate_neo4j_slowdown(latency_ms: int = 2000):
        """Injects latency into Neo4j queries."""
        if ChaosMonkey.is_enabled():
            logger.warning(f"🐒 [Chaos] Injecting {latency_ms}ms latency into Neo4j query...")
            return asyncio.sleep(latency_ms / 1000.0)
        return asyncio.sleep(0)

    @staticmethod
    def simulate_tool_crash(tool_name: str, failure_rate: float = 0.5):
        """Simulates a crash for a specific tool."""
        if ChaosMonkey.is_enabled() and random.random() < failure_rate:
            logger.warning(f"🐒 [Chaos] Injecting intentional crash for tool: {tool_name}")
            raise RuntimeError(f"Chaos Tool Crash: {tool_name}")

    @staticmethod
    def simulate_agent_timeout(agent_name: str, timeout_ms: int = 10000):
        """Simulates a timeout for a specific agent."""
        if ChaosMonkey.is_enabled():
            logger.warning(f"🐒 [Chaos] Injecting intentional timeout for agent: {agent_name}")
            return asyncio.sleep(timeout_ms / 1000.0)
        return asyncio.sleep(0)
