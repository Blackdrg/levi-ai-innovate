import json
import logging
import asyncio
from typing import Dict, Any
from backend.db.redis import r_async as redis_client, HAS_REDIS_ASYNC

logger = logging.getLogger(__name__)

TASK_STREAM = "dcn:task_stream"
SCALING_ALERT_KEY = "dcn:scaling:alerts"

class AutoScaler:
    """
    Sovereign Auto-Scaler v13.1.0.
    Monitors swarm saturation and emits Scaling Cognitive Pulses.
    """

    def __init__(self, check_interval: int = 15):
        self.check_interval = check_interval
        self.is_running = False

    async def start(self):
        """Starts the monitoring loop."""
        self.is_running = True
        logger.info(f"[AutoScaler] Infrastructure Monitor [ACTIVE] ({self.check_interval}s interval)")
        
        while self.is_running:
            try:
                # 1. Check Stream Depth (Backlog)
                depth = await self._get_stream_depth()
                
                # 2. Check Cluster Saturation (VRAM/Slots)
                from ..core.dcn.resource_manager import ResourceManager
                mgr = ResourceManager()
                stats = await mgr.get_cluster_stats()
                
                # 3. Scaling Logic (Heuristic Gate)
                await self._evaluate_scaling(depth, stats)
                
                await asyncio.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"[AutoScaler] Monitor drift: {e}")
                await asyncio.sleep(60)

    async def _get_stream_depth(self) -> int:
        """Counts pending tasks in the Redis Stream."""
        if not HAS_REDIS_ASYNC: return 0
        try:
            # Approximate length for performance
            return await redis_client.xlen(TASK_STREAM)
        except Exception:
            return 0

    async def _evaluate_scaling(self, depth: int, stats: Dict[str, Any]):
        """Evaluates if more workers are needed based on backlog vs capacity."""
        node_count = stats.get("node_count", 0)
        free_gb = stats.get("free_vram_gb", 0)
        
        # Rule 1: Backlog Pressure (Scale Up)
        if depth > (node_count * 5) and node_count < 20: # Arbitrary maxReplicas: 20 from k8s spec
            await self._emit_scaling_alert("SCALE_UP", {
                "reason": "Queue Backlog", 
                "depth": depth, 
                "current_nodes": node_count
            })
        
        # Rule 2: Resource Exhaustion (Scale Up)
        elif free_gb < 2 and node_count < 20:
             await self._emit_scaling_alert("SCALE_UP", {
                "reason": "VRAM Exhaustion", 
                "free_gb": free_gb, 
                "current_nodes": node_count
            })
            
        # Rule 3: Idle Over-provisioning (Scale Down)
        elif depth == 0 and node_count > 1:
            # Check for consistent idleness before scaling down? 
            # For simplicity, we just alert.
            await self._emit_scaling_alert("SCALE_DOWN", {
                "reason": "System Idle", 
                "current_nodes": node_count
            })

    async def _emit_scaling_alert(self, action: str, data: Dict[str, Any]):
        """Publishes a scaling pulse and triggers the local provider if configured."""
        alert = {
            "action": action,
            "data": data,
            "timestamp": asyncio.get_event_loop().time()
        }
        logger.info(f"🚀 [Scaling Event] {action}: {data}")
        
        if HAS_REDIS_ASYNC:
            await redis_client.publish(SCALING_ALERT_KEY, json.dumps(alert))
            await redis_client.setex("dcn:scaling:latest", 600, json.dumps(alert))

        # 🐳 Local Docker Scaling (v2.1 Experimental)
        if os.getenv("ENABLE_LOCAL_DOCKER_SCALING") == "true":
            try:
                provider = DockerComposeProvider()
                current_nodes = data.get("current_nodes", 1)
                new_count = current_nodes + (1 if action == "SCALE_UP" else -1)
                new_count = max(1, min(new_count, 5)) # Limit local scaling
                
                await provider.scale("worker", new_count)
            except Exception as e:
                logger.error(f"[AutoScaler] Docker Scale failed: {e}")

class DockerComposeProvider:
    """Scales local workers using docker-compose (Local Testing Only)."""
    async def scale(self, service_name: str, count: int):
        logger.info(f"[Docker] Scaling {service_name} to {count} replicas...")
        # Use subprocess to run docker-compose scale
        try:
            cmd = ["docker-compose", "up", "-d", "--scale", f"{service_name}={count}"]
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            if process.returncode == 0:
                logger.info(f"[Docker] Successfully scaled to {count}")
            else:
                logger.error(f"[Docker] Scale Error: {stderr.decode()}")
        except Exception as e:
            logger.error(f"[Docker] Command failure: {e}")

    def stop(self):
        self.is_running = False
