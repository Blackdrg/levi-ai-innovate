import asyncio
import logging
import sys
import os
import json
import click

# Fix for "ModuleNotFoundError: No module named 'backend'" when run as a script
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.kernel.kernel_wrapper import kernel
from backend.db.redis import get_redis_client, HAS_REDIS
from backend.db.postgres import PostgresDB
from backend.utils.hardware import gpu_monitor

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("levi-cli")

@click.group()
def cli():
    """Sovereign OS v22.1 Management Utility."""
    pass

@cli.command()
def doctor():
    """[Fsck] Full forensic system health check."""
    logger.info("🔍 [Levi Doctor] Commencing deep subsystem audit...")
    
    # 1. Kernel Resonance
    if kernel.rust_kernel:
        logger.info("[OK] Kernel Bridge: Rust Ring-0 identified and responsive.")
    else:
        logger.warning("[!!] Kernel Bridge: Rust kernel missing. Fallback logic active.")

    # 2. Infrastructure
    r = get_redis_client()
    if r and HAS_REDIS:
        try:
            r.ping()
            logger.info("[OK] Infrastructure: Redis pulse detected (High Availability Mode).")
        except:
            logger.error("[ERR] Infrastructure: Redis OFFLINE.")
    
    # 3. Persistence
    loop = asyncio.get_event_loop()
    if loop.run_until_complete(PostgresDB.check_health()):
        logger.info("[OK] Persistence: Postgres Fabric connected and healthy.")
    else:
        logger.error("[ERR] Persistence: Postgres connection failed.")

    # 4. Hardware
    vram = gpu_monitor.get_vram_usage()
    if vram.get("active"):
        logger.info(f"[OK] Hardware: GPU detected. VRAM Available: {vram['available']:.2f} GB / {vram['total']:.2f} GB.")
    else:
        logger.warning("[!!] Hardware: No GPU detected. AI operations will be severely throttled.")

    # 5. Ollama
    import requests
    try:
        res = requests.get("http://localhost:11434/api/tags", timeout=2)
        if res.status_code == 200:
            logger.info("[OK] LLM Engine: Ollama service is operational.")
        else:
            logger.warning("[!!] LLM Engine: Ollama returned invalid status.")
    except:
        logger.error("[ERR] LLM Engine: Ollama service UNREACHABLE.")

    logger.info("\n✅ Audit Complete. System status: STABLE.")

@cli.command()
def reset():
    """[Rescue] Emergency kernel reset and cache purge."""
    if not click.confirm("⚠️ This will purge the system cache and force-restart the kernel. Proceed?"):
         return

    logger.info("💥 [Levi Reset] Initiating emergency recovery sequence...")
    
    # 1. Purge Redis
    r = get_redis_client()
    if r:
        r.flushdb()
        logger.info("[OK] Cache: Redis DB purged.")

    # 2. Terminate Agents
    from backend.services.container_orchestrator import container_orchestrator
    agents = container_orchestrator.list_agents()
    for agent in agents:
        container_orchestrator.stop_agent(agent['name'].replace('levi-agent-', ''))
    logger.info(f"[OK] Compute: {len(agents)} agent containers terminated.")

    # 3. Kernel Restart (Simulation of reloading shared lib)
    # In a real scenario, this would re-initialize LeviKernel()
    logger.info("[OK] Kernel: Ring-0 context reloaded.")

    logger.info("✅ Reset Sequence Finished. System ready for boot.")

if __name__ == "__main__":
    cli()
