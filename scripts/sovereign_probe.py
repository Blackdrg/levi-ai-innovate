import os
import asyncio
import logging
import time
from typing import Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SovereignProbe")

class SovereignProbe:
    """
    LEVI-AI Sovereign Engine Probe.
    Performs deep diagnostics on the Vector DB and Local Inference layers.
    """

    @staticmethod
    async def run_full_diagnostic() -> Dict[str, Any]:
        results = {
            "timestamp": time.time(),
            "checks": {},
            "status": "healthy"
        }

        # 1. Vector DB Isolation Check
        try:
            from backend.utils.vector_db import VectorDB
            test_id = "probe_test_user"
            # Verify we can access the user-scoped path (even if empty)
            collection = await VectorDB.get_user_collection(test_id, "memory")
            results["checks"]["vector_db"] = {
                "status": "passed",
                "storage_root": collection.storage_path
            }
        except Exception as e:
            results["checks"]["vector_db"] = {"status": "failed", "error": str(e)}
            results["status"] = "degraded"

        # 2. Local LLM Reachability Check
        try:
            from backend.services.orchestrator.local_engine import LocalLLM, HAS_LLAMA_CPP
            if not HAS_LLAMA_CPP:
                results["checks"]["local_llm"] = {"status": "skipped", "reason": "llama-cpp-python not installed"}
            else:
                model_path = os.getenv("LOCAL_MODEL_PATH", "backend/data/models/llama-3-8b-instruct.Q4_K_M.gguf")
                if not os.path.exists(model_path):
                    results["checks"]["local_llm"] = {"status": "degraded", "reason": f"Model weights missing at {model_path}"}
                else:
                    # Quick instance check (not full load unless needed)
                    instance = await LocalLLM.get_instance()
                    results["checks"]["local_llm"] = {
                        "status": "passed" if instance else "failed",
                        "model": model_path
                    }
        except Exception as e:
            results["checks"]["local_llm"] = {"status": "failed", "error": str(e)}
            results["status"] = "degraded"

        # 3. Redis Persistence Check
        try:
            from backend.redis_client import HAS_REDIS, r as redis_client
            if HAS_REDIS:
                ping = redis_client.ping()
                results["checks"]["redis"] = {"status": "passed" if ping else "failed"}
            else:
                results["checks"]["redis"] = {"status": "degraded", "reason": "Redis disabled"}
        except Exception as e:
            results["checks"]["redis"] = {"status": "failed", "error": str(e)}
            results["status"] = "degraded"

        return results

if __name__ == "__main__":
    async def main():
        print("🔍 LEVI-AI Sovereign Engine Probe: Initiating...")
        report = await SovereignProbe.run_full_diagnostic()
        print(f"Status: {report['status'].upper()}")
        for check, data in report["checks"].items():
            print(f" - {check}: {data['status']} {data.get('reason', '')}")
            
    asyncio.run(main())
