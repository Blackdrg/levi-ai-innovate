import asyncio
import logging
import time
from backend.utils.event_bus import sovereign_event_bus

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("pulse_emitter")

class PulseEmitter:
    """
    Sovereign v16.2: Pulse Emitter.
    Heartbeat of the cognitive OS. Emits periodic events to trigger autonomous workers.
    Replaces legacy cron jobs with Redis Stream triggers.
    """
    def __init__(self):
        self.is_running = False

    async def start(self):
        self.is_running = True
        logger.info("💓 Pulse Emitter [ACTIVE]. Emitting periodic system pulses...")
        
        step = 0
        while self.is_running:
            try:
                # 1. System-wide integrity pulse (Every 60s)
                await sovereign_event_bus.emit("system_pulses", {
                    "event_type": "SYSTEM_PULSE",
                    "payload": {"step": step, "type": "integrity_check"},
                    "source": "pulse_emitter"
                })

                # 2. Evolution sweep pulse (Every 10 minutes)
                if step % 10 == 0:
                     await sovereign_event_bus.emit("evolution_events", {
                        "event_type": "EVOLUTION_SWEEP",
                        "payload": {"reason": "scheduled_evolution"},
                        "source": "pulse_emitter"
                    })
                
                # 3. Memory Hygiene pulse (Every 20 minutes)
                if step % 20 == 0:
                     await sovereign_event_bus.emit("memory_events", {
                        "event_type": "MEMORY_HYGIENE",
                        "payload": {"scope": "global"},
                        "source": "pulse_emitter"
                     })

                # 4. Process Health pulse (Every 5 minutes)
                if step % 5 == 0:
                    await sovereign_event_bus.emit("kernel_events", {
                        "event_type": "PROCESS_HEALTH_CHECK",
                        "payload": {"action": "prune_zombies"},
                        "source": "pulse_emitter"
                    })

                # 5. DCN Mesh Consensus Sync (Every 1 minute)
                await sovereign_event_bus.emit("dcn_mesh_sync", {
                    "event_type": "DCN_SYNC_PULSE",
                    "payload": {
                        "node_id": os.getenv("NODE_ID", "node-alpha"),
                        "term": step,
                        "action": "HEARTBEAT_ACK"
                    },
                    "source": "pulse_emitter"
                })

                step += 1
                await asyncio.sleep(60)
            except Exception as e:
                logger.error(f"Pulse Emitter Error: {e}")
                await asyncio.sleep(5)

    def stop(self):
        self.is_running = False

if __name__ == "__main__":
    emitter = PulseEmitter()
    try:
        asyncio.run(emitter.start())
    except KeyboardInterrupt:
        emitter.stop()
