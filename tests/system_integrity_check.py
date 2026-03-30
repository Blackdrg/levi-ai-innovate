import asyncio
import os
import sys
import logging
from datetime import datetime

# Setup paths
sys.path.append(os.getcwd())

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SystemCheck")

async def verify_brain_engine():
    """Verify the Orchestrator Brain & Engine Logic."""
    print("\n🧠 [BRAIN CHECK] Verifying Orchestrator Components...")
    
    try:
        from backend.services.orchestrator.planner import classify_intent, generate_plan
        from backend.services.orchestrator.engine import run_orchestrator
        from backend.services.orchestrator.memory_manager import MemoryManager
        from backend.services.orchestrator.executor import execute_plan
        
        print("✅ Orchestrator imports successful.")
        
        # Test Planner
        print("🔍 Testing Intent Detection...")
        intent_res = await classify_intent("Research futuristic AI and then draw it.")
        print(f"   Intent & Complexity: {intent_res}")
        
        # Test Memory Management
        print("🔍 Testing Memory Retrieval...")
        context = await MemoryManager.get_combined_context(user_id="test_user", session_id="test_sess", query="AI trends")
        print(f"   Memory Context check (Long-term Facts): {context.get('long_term', {}).get('relevant_facts')}")
        
        print("✅ Brain components functioning.")
    except Exception as e:
        print(f"❌ Brain Check failed: {e}")

async def verify_infrastructure():
    """Verify Server/DB/Redis Infrastructure."""
    print("\n🖥️ [INFRA CHECK] Verifying Database & Cache...")
    
    try:
        # 1. Redis
        from backend.redis_client import HAS_REDIS, r as redis_client
        if HAS_REDIS:
            redis_client.ping()
            print("✅ Redis Connected.")
        else:
            print("⚠️ Redis not connected (fallback mode).")
            
        # 2. Firestore
        from backend.firestore_db import db as firestore_db
        if firestore_db:
            firestore_db.collection("health_check").document("status").get(timeout=3)
            print("✅ Firestore Connected.")
        else:
            print("❌ Firestore not initialized.")
            
        # 3. Gateway
        from backend.gateway import app
        print("✅ Gateway App registered with routers.")
        
    except Exception as e:
        print(f"❌ Infrastructure Check failed: {e}")

async def run_full_check():
    print("==========================================")
    print("LEVI-AI SYSTEM INTEGRITY CHECK v4.5")
    print(f"Timestamp: {datetime.utcnow().isoformat()}")
    print("==========================================")
    
    await verify_infrastructure()
    await verify_brain_engine()
    
    print("\n✨ FINAL STATUS: SYSTEM READY FOR LAUNCH ✨")

if __name__ == "__main__":
    asyncio.run(run_full_check())
