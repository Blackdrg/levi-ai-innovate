import json
import logging
from typing import Dict, Any, List, Optional
from backend.db.redis import r_async as redis_client, HAS_REDIS_ASYNC

logger = logging.getLogger(__name__)

class ResourceManager:
    """
    Sovereign DCN Resource Manager v2.0.
    Handles cluster-wide GPU pooling, slot-aware scheduling, and VRAM optimization.
    """

    def __init__(self):
        self.swarm_key = "dcn:swarm:nodes"

    async def get_all_nodes(self) -> List[Dict[str, Any]]:
        """Retrieves and deserializes all active node profiles from the Swarm Registry."""
        if not HAS_REDIS_ASYNC:
            return []
        
        try:
            nodes_raw = await redis_client.hgetall(self.swarm_key)
            nodes = []
            for node_id, data_json in nodes_raw.items():
                try:
                    nodes.append(json.loads(data_json))
                except json.JSONDecodeError:
                    continue
            return nodes
        except Exception as e:
            logger.error(f"[ResourceManager] Failed to reach Swarm Registry: {e}")
            return []

    async def find_optimal_node(
        self, 
        model_tier: str, 
        required_capability: str = "llm",
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        Heuristic-based node selection for Task Dispatch.
        Prioritizes nodes with:
        1. Required Capability (v2.1 specialized tasks)
        2. Resident Model (v1: Pre-pinned)
        3. Maximum Free VRAM
        """
        nodes = await self.get_all_nodes()
        if not nodes:
            return None
        
        # 🛡️ Audit Point: Capability Gate
        nodes = [n for n in nodes if required_capability in n.get("capabilities", ["llm"])]
        if not nodes:
            logger.warning(f"[ResourceManager] No node has capability: {required_capability}")
            return None

        # Filter nodes by those that have at least one slot matching VRAM requirements
        # (Tier requirements mapped same as VRAMGuard)
        tier_requirements = {
            "L1": 2048, "L2": 6144, "L3": 24576, "L4": 40960
        }
        req_mb = tier_requirements.get(model_tier, 6144)

        eligible_nodes = []
        for node in nodes:
            # Check if any device slot can fit the tier
            slots = node.get("device_slots", [])
            can_fit = any(s.get("vram_free_mb", 0) >= req_mb for s in slots)
            
            if can_fit:
                # 🛠️ Advanced Scoring: VRAM + Load + Latency
                vram_score = sum(s.get("vram_free_mb", 0) for s in slots) / 1024 # GB free
                load_score = (100 - node.get("cpu_percent", 50)) / 10.0
                
                # Latency Score: Inverse of RTT (Max 10 points)
                # 0ms = 10, 500ms = 0
                rtt = node.get("rtt_ms", 100)
                latency_score = max(0, (500 - rtt) / 50.0)
                
                eligible_nodes.append({
                    "node_id": node.get("node_id"),
                    "score": vram_score + load_score + latency_score
                })

        if not eligible_nodes:
            logger.warning(f"[ResourceManager] No node has capacity for {model_tier} ({req_mb}MB required).")
            return None

        # Sort by score descending
        eligible_nodes.sort(key=lambda x: x["score"], reverse=True)
        best_node = eligible_nodes[0]["node_id"]
        
        logger.info(f"[ResourceManager] Optimal Node Selected: {best_node} (Score: {eligible_nodes[0]['score']:.2f})")
        return best_node

    async def get_cluster_stats(self) -> Dict[str, Any]:
        """Aggregates cluster capacity for UI/Monitoring."""
        nodes = await self.get_all_nodes()
        return {
            "node_count": len(nodes),
            "total_vram_gb": sum(n.get("vram_total_mb", 0) for n in nodes) / 1024,
            "free_vram_gb": sum(n.get("vram_free_mb", 0) for n in nodes) / 1024,
            "total_device_slots": sum(len(n.get("device_slots", [])) for n in nodes)
        }
