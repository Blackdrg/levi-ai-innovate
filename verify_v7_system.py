import asyncio
import sys
import os
import json
import logging

# Add project root to path
sys.path.append(os.getcwd())

# Set up logging for verification
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from backend.core.brain import LeviBrain
from backend.auth import UserIdentity

async def verify_system():
    print("🚀 Starting LEVI-AI Sovereign OS v7 Unified System Verification...")
    
    brain = LeviBrain()
    test_identity = UserIdentity(user_id="test_user_777", role="admin", tier="pro")
    
    test_queries = [
        "Explain quantum computing in simple terms", # CHAT / KNOWLEDGE
        "Generate a futuristic city image with neon lights", # VISUAL_STUDIO (Agent Routing)
        "Who is the current Prime Minister of the UK?", # SEARCH (Agent Routing)
        "Write a python script to calculate Fibonacci numbers" # CODE (Agent Routing)
    ]
    
    results = []
    
    for query in test_queries:
        print(f"\n--- 🧠 Testing Unified Engine with Query: '{query}' ---")
        full_response = ""
        events_received = []
        
        try:
            # Engage the production LeviBrain (streaming=True)
            # Standard signatures: user_id, user_input, session_id, streaming, user_tier, mood
            stream = await brain.route(
                user_id=test_identity.user_id,
                user_input=query,
                session_id="verify_session",
                streaming=True,
                user_tier=test_identity.tier,
                mood="philosophical"
            )
            
            async for chunk in stream:
                if "token" in chunk:
                    print(chunk["token"], end="", flush=True)
                    full_response += chunk["token"]
                elif "event" in chunk:
                    evt = chunk["event"]
                    data = str(chunk.get("data", ""))[:30]
                    print(f"\n  [EVENT] {evt}: {data}...")
                    events_received.append(evt)
            
            print(f"\n  [MISSION COMPLETE] Result size: {len(full_response)} chars")
            
            # Validation Checks (v7 Standard: activity, metadata, token)
            has_activity = "activity" in events_received
            has_metadata = "metadata" in events_received
            has_tokens = len(full_response) > 0
            
            status = "✅ PASS" if (has_activity and has_metadata and has_tokens) else "❌ FAIL"
            results.append({"query": query, "status": status, "events": list(set(events_received))})
            
        except Exception as e:
            print(f"\n  [ENGINE ANOMALY] {e}")
            results.append({"query": query, "status": "❌ ERROR", "error": str(e)})

    print("\n--- 📊 SOVEREIGN UNIFICATION REPORT ---")
    for res in results:
        print(f"{res['status']} | {res['query']} | Events: {res.get('events', 'N/A')}")
    
    # Final Persistence Verification
    from backend.core.memory_manager import MemoryManager
    logger.info("Verifying Long-Term Memory (LTM) Persistence...")
    context = await MemoryManager.get_combined_context(test_identity.user_id, "verify_session", "test")
    if context.get("history"):
        print("✅ PASS | Memory Vault Connected & Persistent")
    else:
        print("❌ FAIL | Memory Pulse missing historical resonance")

if __name__ == "__main__":
    asyncio.run(verify_system())
