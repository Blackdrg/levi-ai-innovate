import json
import logging
import asyncio
from typing import Optional, Dict, Any, List
from backend.db.redis import get_redis_client, HAS_REDIS

logger = logging.getLogger(__name__)

class DCNLoadBalancer:
    """
    Sovereign DCN Auto-scaling Load Balancer.
    Reads node heartbeats from Redis hashes to route incoming missions to the least-utilized worker.
    """
    
    def __init__(self):
        self.redis = get_redis_client()
        self.node_registry_key = "dcn:nodes:registry"

    async def get_optimal_node(self, required_capabilities: List[str] = None) -> Optional[str]:
        """
        Calculates the least-utilized node based on CPU and memory metrics reported via DCN Protocol.
        """
        if not HAS_REDIS or not self.redis:
            return None

        try:
            nodes_data = self.redis.hgetall(self.node_registry_key)
            if not nodes_data:
                return None

            best_node = None
            lowest_load_score = float('inf')

            for node_id_bytes, metric_bytes in nodes_data.items():
                node_id = node_id_bytes.decode('utf-8')
                try:
                    metrics = json.loads(metric_bytes.decode('utf-8'))
                    
                    # Check capabilities
                    if required_capabilities:
                        caps = metrics.get("capabilities", [])
                        if not all(c in caps for c in required_capabilities):
                            continue

                    # Predictive Load Score = (CPU * 0.6) + (Mem * 0.4) 
                    # Can factor in VRAM if LLM is required
                    cpu = metrics.get("cpu_percent", 100.0)
                    mem = metrics.get("memory_percent", 100.0)
                    score = (cpu * 0.6) + (mem * 0.4)

                    if score < lowest_load_score:
                        lowest_load_score = score
                        best_node = node_id

                except json.JSONDecodeError:
                    continue

            if best_node:
                logger.info(f"[LoadBalancer] Selected optimal DCN node: {best_node} (Score: {lowest_load_score:.2f})")
            return best_node

        except Exception as e:
            logger.error(f"[LoadBalancer] Failed to get optimal node: {e}")
            return None

    def register_node_heartbeat(self, node_id: str, metadata: Dict[str, Any]):
        """Called by DCN Protocol to register active metrics."""
        if not HAS_REDIS or not self.redis:
            return
            
        try:
            self.redis.hset(self.node_registry_key, node_id, json.dumps(metadata))
            # TTL handled by a separate reaper or we just use setex for individual keys
            # For HSET we can't set individual field TTLs easily in older Redis, 
            # so we'll rely on timestamps in a production HPA setup.
            self.redis.expire(self.node_registry_key, 120) 
        except Exception as e:
            logger.error(f"[LoadBalancer] Heartbeat registration failed: {e}")

# Global instance
dcn_balancer = DCNLoadBalancer()
