# backend/services/rust_runtime_bridge.py
import httpx
import logging
import os

logger = logging.getLogger("levi.rust_bridge")

RUST_RUNTIME_URL = os.getenv("RUST_RUNTIME_URL", "http://127.0.0.1:8001")

class RustRuntimeBridge:
    def __init__(self):
        self.client = httpx.AsyncClient(base_url=RUST_RUNTIME_URL, timeout=10.0)

    async def admit_mission(self, task_description: str) -> dict:
        """Proxies a mission request to the native Rust LEVI Core Runtime."""
        try:
            logger.info(f"🚀 [RustBridge] Proxying mission to native runtime: {task_description[:50]}...")
            response = await self.client.post("/mission/admit", json={"task": task_description})
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"❌ [RustBridge] Native Runtime communication failed: {e}")
            return {"status": "error", "message": str(e)}

    async def check_health(self) -> bool:
        try:
            response = await self.client.get("/status")
            return response.status_code == 200
        except:
            return False

rust_bridge = RustRuntimeBridge()
