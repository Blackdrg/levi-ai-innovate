import os
import aiohttp
import asyncio
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class LeviClient:
    """
    Sovereign v14.0 Python SDK.
    Provides an interface to the Distributed Cognitive Network APIs.
    """
    def __init__(self, api_key: str = None, base_url: str = None):
        self.api_key = api_key or os.getenv("LEVI_API_KEY")
        self.base_url = (base_url or os.getenv("LEVI_API_URL", "http://localhost:8000")).rstrip("/")
        
        if not self.api_key:
            logger.warning("[LeviClient] Warning: Initialized without API key. Rate limits will strictly apply.")

    def _headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    async def execute_mission(self, prompt: str, session_id: str = "default", **kwargs) -> Dict[str, Any]:
        """
        Submits a cognitive mission to the LEVI-AI orchestrator.
        """
        payload = {
            "prompt": prompt,
            "session_id": session_id,
            "tier": kwargs.get("tier", "seeker")
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{self.base_url}/api/v1/mission", json=payload, headers=self._headers()) as response:
                if response.status != 200:
                    text = await response.text()
                    raise Exception(f"Mission failed with status {response.status}: {text}")
                return await response.json()

    async def fetch_trace(self, request_id: str) -> Dict[str, Any]:
        """
        Fetches the deterministic execution trace for a specific mission.
        """
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.base_url}/api/v1/traces/{request_id}", headers=self._headers()) as response:
                if response.status != 200:
                    text = await response.text()
                    raise Exception(f"Failed to fetch trace with status {response.status}: {text}")
                return await response.json()

    # Sync Wrappers for ease of use
    def execute_mission_sync(self, prompt: str, session_id: str = "default", **kwargs) -> Dict[str, Any]:
        return asyncio.run(self.execute_mission(prompt, session_id, **kwargs))
