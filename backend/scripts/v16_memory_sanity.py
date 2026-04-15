"""
Sovereign Memory Sanity Test v16.1.
Validates the 4-Tier Memory Integration (Redis, Postgres, FAISS, Neo4j).
"""

import asyncio
import logging
from backend.core.memory_manager import MemoryManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("memory_sanity")

async def test_memory_swarm():
    mm = MemoryManager()
    await mm.initialize()
    
    user_id = "test_sovereign_user"
    session_id = "test_session_42"
    
    print("\n🔍 [MemorySanity] Validating 4-Tier Cognitive Fabric...")
    
    # 1. Tier 1/2 Check (Redis/Postgres)
    print("⏳ [Tier 1/2] Pulsing Working & Episodic Memory...")
    await mm.store(
        user_id=user_id,
        session_id=session_id,
        user_input="LEVI, remember that my encryption key is stored in the local vault.",
        response="Acknowledged. I have recorded the location of your encryption key.",
        perception={"intent": "info"},
        results=[]
    )
    
    # 2. Tier 3 Check (FAISS Vector)
    print("⏳ [Tier 3] Testing Semantic Retrieval...")
    context = await mm.get_unified_context(user_id, session_id, query="where is my encryption key?")
    
    found_in_vector = False
    for fact in context.get("long_term", {}).get("raw", []):
        if "encryption key" in (fact.get("fact") or "").lower():
            found_in_vector = True
            break
    
    if found_in_vector:
        print("✅ [Tier 3] Vector retrieval SUCCESS.")
    else:
        print("❌ [Tier 3] Vector retrieval FAILED.")

    # 3. Tier 4 Check (Neo4j Graph)
    print("⏳ [Tier 4] Testing Graph Resonance...")
    # Triggering resonance check
    graph_data = context.get("long_term", {}).get("graph_resonance", [])
    print(f"✅ [Tier 4] Graph returned {len(graph_data)} resonance nodes.")

    # 4. Integrity Report
    integrity = await mm.check_cognitive_integrity()
    print(f"\n🏆 Final Integrity Report: {integrity['overall_fidelity'] * 100}% Operational")
    for tier, status in integrity["tiers"].items():
        print(f"  - {tier}: {status}")

    await mm.shutdown()

if __name__ == "__main__":
    asyncio.run(test_memory_swarm())
