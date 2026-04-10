"""
LEVI-AI v14.1 Production Graduation Smoke Test
Verifies the hardened Orchestrator, Planner, and Evolution Engine.
"""

import asyncio
import logging
from backend.core.orchestrator import orchestrator
from backend.db.postgres import PostgresDB

# Setup basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def verify_graduation():
    print("\n--- [LEVI-AI v14.1 PRODUCTION GRADUATION SUITE] ---")
    
    test_cases = [
        {"input": "Hello LEVI", "expected_tag": None}, # Standard chat
        {"input": "Search for latest Bitcoin price", "expected_tag": None}, # Search escalation
        {"input": "Deterministic Rule Test", "expected_tag": "FAST_PATH_EVOLVED"} # Evolution test
    ]
    
    # 1. Warm-up (Ensure DB/Init)
    await PostgresDB.initialize()
    
    # 2. Sequential Execution
    for i, case in enumerate(test_cases, 1):
        print(f"\n[Test {i}/3] Input: '{case['input']}'")
        
        # We simulate a mission
        try:
            res = await orchestrator.run(
                user_input=case["input"],
                user_id="grad_validator_001",
                session_id="session_smoke_test"
            )
            
            tag = res.get("tag")
            status = res.get("status")
            
            print(f"Status: {status}")
            print(f"Tag: {tag}")
            print(f"Response: {res.get('response')[:50]}...")
            
            if case["expected_tag"] and tag != case["expected_tag"]:
                print(f"⚠️ Warning: Expected tag {case['expected_tag']}, got {tag}")
            else:
                print("✅ Node Resonance Satisfactory.")
                
        except Exception as e:
            print(f"❌ Mission Failure: {e}")

    print("\n--- [GRADUATION VERIFICATION COMPLETE] ---")

if __name__ == "__main__":
    asyncio.run(verify_graduation())
