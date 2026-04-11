# backend/services/ollama_health.py
import logging
import asyncio
import os
import aiohttp
from typing import Dict, Any, Optional
from backend.db.redis_client import r as redis_client, HAS_REDIS

logger = logging.getLogger(__name__)

class OllamaModelMonitor:
    """
    Sovereign v15.0: Model Tier Liveness Monitor.
    Tracks local Ollama/llama-cpp-python health via local Bolt/HTTP heartbeats.
    """
    def __init__(self):
        self.host = os.getenv("OLLAMA_HOST", "localhost")
        self.port = os.getenv("OLLAMA_PORT", "11434")
        self.endpoint = f"http://{self.host}:{self.port}/api/tags"
        self._is_running = False
        self._check_task: Optional[asyncio.Task] = None

    async def start(self):
        if self._is_running: return
        self._is_running = True
        self._check_task = asyncio.create_task(self._health_loop())
        logger.info(f"[Monitor] Ollama Model Tier monitor active ({self.endpoint})")

    async def stop(self):
        self._is_running = False
        if self._check_task:
            self._check_task.cancel()
            try: await self._check_task
            except asyncio.CancelledError: pass

    async def check_health(self) -> Dict[str, Any]:
        """Performs a single liveness check on the model tier."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.endpoint, timeout=2.0) as response:
                    if response.status == 200:
                        data = await response.json()
                        return {"status": "healthy", "models": len(data.get("models", []))}
                    return {"status": "unhealthy", "code": response.status}
        except Exception as e:
            return {"status": "offline", "error": str(e)}

    async def _health_loop(self):
        """Background loop to update Redis health state."""
        while self._is_running:
            health = await self.check_health()
            if HAS_REDIS:
                # Store core health status for orchestrator gates
                redis_client.set("health:ollama:status", health["status"], ex=60)
                if health["status"] == "healthy":
                    redis_client.set("health:ollama:last_seen", str(asyncio.get_event_loop().time()), ex=60)
            
            if health["status"] != "healthy":
                logger.warning(f"[Monitor] Model Tier ALERT: {health['status']} - {health.get('error', 'Inaccessible')}")
            
            await asyncio.sleep(30)

ollama_monitor = OllamaModelMonitor()
