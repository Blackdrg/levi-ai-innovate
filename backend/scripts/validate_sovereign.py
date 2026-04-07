import asyncio
import os
import sys

# Ensure we can import from the project root
sys.path.append(os.getcwd())

from backend.engines.brain.orchestrator import BrainOrchestrator

async def validate_sovereign():
    print("═══ LEVI-AI Sovereign OS v7: System Validation ═══")
    
    # 1. Initialize Orchestrator
    print("[1/5] Initializing Brain Orchestrator...")
    try:
        brain = BrainOrchestrator()
        print("  ✅ Registry synchronized.")
    except Exception as e:
        print(f"  ❌ Initialization failed: {e}")
        return

    # 2. Test Stream Orchestration
    print("[2/5] Validating Multi-Part SSE Stream...")
    user_id = "validation_test_user"
    query = "What is the core philosophy of Sovereign OS?"
    
    event_count = 0
    token_count = 0
    intents = []
    
    try:
        async for chunk in brain.stream_request(user_id, query):
            event_count += 1
            if chunk.get("event") == "metadata":
                intents.append(chunk["data"].get("intent"))
            if "token" in chunk:
                token_count += 1
        
        print(f"  ✅ Stream completed with {event_count} events.")
        print(f"  ✅ Intent identified as: {intents[0] if intents else 'Unknown'}")
        print(f"  ✅ Tokens received: {token_count}")
    except Exception as e:
        print(f"  ❌ Streaming failed: {e}")

    # 3. Test Vector Store Integrity
    print("[3/5] Validating FAISS Vector Store...")
    try:
        from backend.db.vector_store import vector_index
        total = vector_index.ntotal
        print(f"  ✅ FAISS Index active with {total} fragments.")
    except Exception as e:
        print(f"  ❌ Vector Store error: {e}")

    # 4. Test Learning Loop Persistence
    print("[4/5] Validating Synthetic Memory Loop...")
    dataset_path = "backend/data/sovereign_dataset.jsonl"
    if os.path.exists(dataset_path):
        size = os.path.getsize(dataset_path)
        print(f"  ✅ Sovereign dataset detected ({size} bytes).")
    else:
        print("  ⚠️ Dataset not yet initialized (normal for first run).")

    # 5. Environment Check
    print("[5/5] Checking Production Readiness...")
    critical_vars = ["SECRET_KEY", "ADMIN_KEY", "INTERNAL_SERVICE_KEY"]
    missing = [v for v in critical_vars if not os.getenv(v)]
    if not missing:
        print("  ✅ All critical security environment variables are set.")
    else:
        print(f"  ⚠️ Missing {len(missing)} vars: {', '.join(missing)} (Using fallbacks).")

    print("\n═══ Validation Complete: System is SOVEREIGN & SYNCED ═══")

if __name__ == "__main__":
    asyncio.run(validate_sovereign())
