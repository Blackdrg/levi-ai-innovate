
import os
import asyncio
from unittest.mock import MagicMock, patch
import logging

# Set production environment
os.environ["ENVIRONMENT"] = "production"
os.environ["SECRET_KEY"] = "test_secret_key_at_least_32_chars_long"
os.environ["RAZORPAY_KEY_ID"] = "test"
os.environ["RAZORPAY_KEY_SECRET"] = "test"
os.environ["RAZORPAY_WEBHOOK_SECRET"] = "test"
os.environ["ADMIN_KEY"] = "test"
os.environ["FIREBASE_PROJECT_ID"] = "test-project"
os.environ["FIREBASE_SERVICE_ACCOUNT_JSON"] = "{}"

# Mocking Firestore for safe local validation if needed
with patch("backend.firestore_db.db", mock_db):
    from backend.main import app, lifespan
    from backend.redis_client import r as redis_client, HAS_REDIS
    from backend.services.orchestrator.memory_utils import FaissMemory, GlobalPatternMemory
    
    async def test_startup_stack():
        print("\n--- 🕵️ LEVI-AI Sovereign Stack Probe ---")
        
        # 1. Redis Check
        if HAS_REDIS:
            try:
                redis_client.ping()
                print("✅ Redis: Online (Ping/Pong successful)")
            except Exception as e:
                print(f"❌ Redis: Connection Failed - {e}")
        else:
            print("⚠️ Redis: Offline (HAS_REDIS is False)")

        # 2. FAISS Memory Check
        try:
            await FaissMemory._init_engine()
            print(f"✅ FAISS (User): Loaded ({FaissMemory._index.ntotal} records)")
            await GlobalPatternMemory._init_engine()
            print(f"✅ FAISS (Global): Loaded ({GlobalPatternMemory._index.ntotal} patterns)")
        except Exception as e:
            print(f"❌ FAISS: Initialization Failed - {e}")

        # 3. API Connectivity (Together AI)
        together_key = os.getenv("TOGETHER_API_KEY")
        if together_key:
            print("✅ Together AI: API Key Detected")
        else:
            print("⚠️ Together AI: API Key Missing")

        # 4. Lifespan Integration
        print("\nTesting lifespan startup...")
        try:
            async with lifespan(app) as _:
                print("✅ Lifespan: Initialized successfully.")
        except Exception as e:
            print(f"❌ Lifespan: Failed to start - {e}")

    if __name__ == "__main__":
        asyncio.run(test_startup_stack())
