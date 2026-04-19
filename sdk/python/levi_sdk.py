# sdk/python/levi_sdk.py
import httpx
import asyncio
import uuid
import logging

logger = logging.getLogger("levi_sdk")

class LeviClient:
    """
    The official LEVI-AI Python SDK for building on a Sovereign OS.
    Allows developers to admit missions, track swarms, and interact with the native core.
    """
    def __init__(self, base_url: str = "http://127.0.0.1:8001"):
        self.base_url = base_url
        self.client = httpx.AsyncClient(base_url=base_url, timeout=30.0)

    async def check_status(self):
        """Checks the health and version of the LEVI Core Runtime."""
        resp = await self.client.get("/status")
        return resp.json()

    async def admit_mission(self, task: str):
        """
        Admits a new mission to the Workflow Engine.
        Returns the unique mission_id.
        """
        logger.info(f" 📥 [SDK] Admitting mission: {task[:50]}...")
        resp = await self.client.post("/mission/admit", json={"task": task})
        resp.raise_for_status()
        return resp.json()["mission_id"]

    async def wait_for_completion(self, mission_id: str, poll_interval: float = 1.0):
        """Polls for mission completion status (Simplification)."""
        # In a real implementation, this would connect to a websocket or query a ledger
        logger.info(f" 🕒 [SDK] Waiting for mission {mission_id} to resolve...")
        await asyncio.sleep(2.0)
        return {"status": "SUCCESS", "mission_id": mission_id}

class BaseAgent:
    """Base class for creating high-level Python agents that interact with LEVI."""
    def __init__(self, client: LeviClient):
        self.client = client

    async def run(self, input_text: str):
        mid = await self.client.admit_mission(input_text)
        return await self.client.wait_for_completion(mid)
