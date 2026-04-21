import asyncio
import logging
import sys
import os

# Ensure backend is in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from backend.engines.brain.orchestrator import orchestrator
from backend.redis_client import cache

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("VerifyEngine")

async def test_mission():
    print("🚀 Starting Cognitive Engine Integration Test...")
    query = "Research the impact of quantum computing on modern cryptography and summarize findings."
    user_id = "test_user_001"
    
    print(f"Query: {query}\n")
    
    try:
        async for event in orchestrator.stream_request(user_id, query):
            if "event" in event:
                print(f"📡 [Event] {event['event']}: {event.get('data')}")
            elif "token" in event:
                # print(event["token"], end="", flush=True)
                pass
                
        print("\n✅ Mission stream complete.")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_mission())
