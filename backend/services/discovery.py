# backend/services/discovery.py
import os
import json
import logging
import asyncio
from typing import List, Dict, Optional
from backend.db.redis import r_async as redis_async

logger = logging.getLogger("service_discovery")

class ServiceDiscovery:
    """
    Sovereign v17.5: Dynamic Service Discovery.
    Registers and tracks active cognitive nodes in the DCN mesh.
    """
    def __init__(self, ttl: int = 60):
        self.ttl = ttl
        self.node_id = os.getenv("NODE_ID", "standalone-node")
        self.region = os.getenv("GCP_REGION", "local")

    async def register_node(self):
        """Registers the current node in the global registry."""
        node_info = {
            "node_id": self.node_id,
            "region": self.region,
            "endpoint": f"{os.getenv('SERVICE_IP', 'localhost')}:8000",
            "last_seen": asyncio.get_event_loop().time()
        }
        
        # 🛰️ Register in Redis with TTL for heartbeat-based discovery
        key = f"dcn:discovery:{self.node_id}"
        await redis_async.set(key, json.dumps(node_info), ex=self.ttl)
        logger.info(f" 🛰️ [DISCOVERY] Node {self.node_id} published to mesh registry.")

    async def get_active_nodes(self) -> List[Dict]:
        """Returns a list of all active nodes in the mesh."""
        keys = await redis_async.keys("dcn:discovery:*")
        nodes = []
        for key in keys:
            data = await redis_async.get(key)
            if data:
                nodes.append(json.loads(data))
        return nodes

    async def start_heartbeat_loop(self):
        """Maintains node registration in the mesh."""
        logger.info(" [DISCOVERY] Heartbeat loop started.")
        while True:
            try:
                await self.register_node()
                await asyncio.sleep(self.ttl // 2)
            except Exception as e:
                logger.error(f" [DISCOVERY] Heartbeat failed: {e}")
                await asyncio.sleep(10)

service_discovery = ServiceDiscovery()
