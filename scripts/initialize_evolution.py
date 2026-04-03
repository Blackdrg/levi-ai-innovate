import os
import sys
import logging
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from backend.core.learning_tasks import unbound_training_cycle

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("EvolutionInit")

def trigger():
    """Manually triggers the first Global Evolution Cycle."""
    logger.info("🚀 Initializing the first Global Evolution Cycle (Phase 6: Unbound Training Array)...")
    
    # We trigger the task directly. In a production environment with Celery, 
    # we would use unbound_training_cycle.delay(), but for manual initialization 
    # and immediate feedback, we run it synchronously here if needed, 
    # OR we trigger it via the Celery app if it's running.
    
    try:
        # Run the task logic
        unbound_training_cycle()
        logger.info("✅ Evolution cycle task successfully queued/executed.")
    except Exception as e:
        logger.error(f"❌ Failed to initialize evolution cycle: {e}")

if __name__ == "__main__":
    trigger()
