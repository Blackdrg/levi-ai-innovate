import asyncio
import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), "backend"))

async def test_debate_loop():
    print("--- Testing LeviBrain v8 Phase 4 (Autonomous Debate Loop) ---")
    
    from backend.core.brain import LeviBrain
    brain = LeviBrain()
    
    user_id = "test_user_debate"
    # A complex prompt that might trigger a critic loop or benefit from refinement
    message = "Analyze the socio-economic impact of colonizing Mars on Earth's current mining industry."
    
    print(f"\n1. Testing Brain with Debate (Streaming)...")
    try:
        count = 0
        async for chunk in await brain.route(message, user_id, "test_sess", streaming=True):
            if chunk.get("event") == "activity":
                print(f"[Activity] {chunk.get('data')}")
            if "Refinement Cycle" in str(chunk.get("data", "")):
                print("🔥 Refinement Cycle Detected!")
            count += 1
            if count > 20: break
        print("✅ Debate Loop test (Streaming) complete.")
    except Exception as e:
        print(f"❌ Debate Loop test failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_debate_loop())
