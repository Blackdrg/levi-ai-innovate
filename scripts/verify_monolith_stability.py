import asyncio
import logging
import time
import random
from typing import List, Dict
from backend.core.brain import LeviBrain
from backend.services.resonance import resonance_engine
from backend.utils.metrics import MetricsHub

# Production-grade Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger("KernelStability")

class StabilityTester:
    """
    Sovereign v22.1: Kernel Stability Audit.
    Executes a high-cycle stress test (10,000 missions) to verify substrate integrity.
    """
    def __init__(self, cycles: int = 10000, concurrency: int = 20):
        self.cycles = cycles
        self.concurrency = concurrency
        self.brain = LeviBrain()
        self.results = {"success": 0, "failure": 0, "anomalies": 0}
        self.latencies = []

    async def run_single_mission(self, cycle_id: int):
        """Simulates a single mission cycle."""
        start_ts = time.time()
        user_id = f"tester_{cycle_id % 100}"
        prompt = f"Stability Test Pulse {cycle_id}: Verify resonance integrity."
        
        try:
            # We use the brain's internal routing to bypass heavy LLM for the bulk of cycles
            # if the cycle_id isn't a 'canary' cycle.
            is_canary = (cycle_id % 100 == 0)
            
            if is_canary:
                logger.info(f"🔍 [Stability] Cycle {cycle_id}: Executing Canary Mission...")
            
            # Execute mission
            res = await self.brain.route(
                user_input=prompt,
                user_id=user_id,
                session_id=f"stability_{cycle_id}",
                request_id=f"STAB-{cycle_id}"
            )
            
            latency = (time.time() - start_ts) * 1000
            self.latencies.append(latency)
            
            if res.get("fidelity", 0) > 0.8:
                self.results["success"] += 1
            else:
                self.results["anomalies"] += 1
                
        except Exception as e:
            logger.error(f"💥 [Stability] Cycle {cycle_id} FAILED: {e}")
            self.results["failure"] += 1

    async def run_audit(self):
        """Main audit loop."""
        logger.info(f"🚀 INITIALIZING 10,000 CYCLE KERNEL STABILITY AUDIT...")
        start_time = time.time()
        
        # Batching for performance
        batch_size = self.concurrency
        for i in range(0, self.cycles, batch_size):
            tasks = []
            for j in range(i, min(i + batch_size, self.cycles)):
                tasks.append(self.run_single_mission(j))
            
            await asyncio.gather(*tasks)
            
            if i % 500 == 0:
                elapsed = time.time() - start_time
                avg_lat = sum(self.latencies[-100:]) / 100 if self.latencies else 0
                logger.info(
                    f"📊 Progress: {i}/{self.cycles} | "
                    f"S: {self.results['success']} F: {self.results['failure']} A: {self.results['anomalies']} | "
                    f"Avg Latency: {avg_lat:.1f}ms | Elapsed: {elapsed:.1f}s"
                )
                
                # Check for resonance drift
                resonance = await resonance_engine.get_resonance_snapshot()
                if resonance["status"] != "STABLE":
                     logger.warning(f"⚠️ [Stability] Resonance Alert: {resonance['status']} at cycle {i}")

        total_time = time.time() - start_time
        logger.info("====================================================")
        logger.info(f"🏁 STABILITY AUDIT COMPLETE in {total_time:.1f}s")
        logger.info(f"Total Cycles: {self.cycles}")
        logger.info(f"Success Rate: {(self.results['success']/self.cycles)*100:.2f}%")
        logger.info(f"Avg Latency: {sum(self.latencies)/len(self.latencies):.2f}ms")
        logger.info(f"Throughput: {self.cycles / total_time:.2f} cycles/sec")
        logger.info("====================================================")

if __name__ == "__main__":
    import sys
    cycles = 10000
    if len(sys.argv) > 1:
        cycles = int(sys.argv[1])
        
    tester = StabilityTester(cycles=cycles)
    try:
        asyncio.run(tester.run_audit())
    except KeyboardInterrupt:
        logger.info("Audit aborted.")
