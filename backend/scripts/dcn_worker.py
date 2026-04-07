import os
import asyncio
import logging
import sys

# Ensure backend is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from backend.core.executor.distributed import DistributedGraphExecutor
from backend.core.dcn_protocol import DCNProtocol
from backend.db.redis import r_async, HAS_REDIS_ASYNC
from backend.config.system import SOVEREIGN_VERSION

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("dcn.worker")

async def main():
    logger.info(f"🚀 Starting LEVI-AI DCN Worker v2.0 (Stack: {SOVEREIGN_VERSION})")
    
    # 1. Redis Connection Check with Retry logic
    retry_count = 0
    max_retries = 3
    
    while retry_count < max_retries:
        try:
            if r_async and await r_async.ping():
                break
        except Exception:
            retry_count += 1
            logger.warning(f"⚠️ Redis not ready (Attempt {retry_count}/{max_retries}). Retrying in 2s...")
            await asyncio.sleep(2)
    
    if not HAS_REDIS_ASYNC:
        logger.error("❌ Redis connection failed. DCN Worker cannot start without Redis.")
        logger.info("💡 TIP: Ensure your local Redis server is running.")
        logger.info("👉 Try: 'docker-compose up -d redis' if using the Sovereign stack.")
        return

    node_id = os.getenv("DCN_NODE_ID", f"worker-{os.getpid()}")
    concurrency = int(os.getenv("WORKER_CONCURRENCY", "4"))
    
    logger.info(f"📍 Node ID: {node_id}")
    logger.info(f"⚙️ Concurrency: {concurrency} nodes")

    # 🛡️ DCN Gossip Layer (v2.0)
    try:
        dcn = DCNProtocol()
        if dcn.is_active:
            # 1. Start Listener
            async def gossip_handler(pulse):
                 if pulse.get("type") == "cognitive_gossip":
                    logger.info(f"📡 Cognitive Pulse: mission {pulse.get('mission_id')[:8]}")
            
            await dcn.start_listener(gossip_handler)
            logger.info("📡 Gossip Listener: [ACTIVE]")

            # 2. Start Autonomous Heartbeat
            os.environ["NODE_ROLE"] = "worker"
            await dcn.start_heartbeat(interval=30)
            logger.info("💓 Heartbeat: [ENABLED]")
    except Exception as e:
        logger.error(f"[DCN] Gossip failure: {e}")

    # 🚀 Auto-Scaling Monitor (Coordinator Only)
    if os.getenv("NODE_ROLE") == "coordinator":
        from backend.services.autoscaler import AutoScaler
        scaler = AutoScaler()
        asyncio.create_task(scaler.start())
        logger.info("📐 Auto-Scaling: [ACTIVE]")

    worker = DistributedGraphExecutor(r_async)
    
    try:
        await worker.worker_loop()
    except KeyboardInterrupt:
        logger.info("🛑 Worker shutting down...")
        worker.stop()
    except Exception as e:
        logger.exception(f"💥 Worker crashed: {e}")

if __name__ == "__main__":
    asyncio.run(main())
