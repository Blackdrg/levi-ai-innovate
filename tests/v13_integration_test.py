import asyncio
from app.brain.controller import BrainCoreController

async def test_v13_flow():
    print("🚀 Initiating v13 Integration Test...")
    brain = BrainCoreController()
    
    prompt = "Analyze the ethical implications of autonomous AI agents in a sovereign ecosystem."
    user_id = "test_user_01"
    threshold = 0.90
    
    print(f"📝 Prompt: {prompt}")
    
    events = []
    async for event_type, payload in brain.run_mission(prompt, user_id, threshold):
        print(f"📡 [EVENT: {event_type.upper()}] {payload}")
        events.append(event_type)
        
    print("\n📊 Mission Pulse Summary:")
    expected = ["perception", "memory", "planning", "execution", "audit", "final"]
    for step in expected:
        status = "✅" if step in events else "❌"
        print(f"{status} {step.capitalize()}")

    if "final" in events:
        print("\n✅ v13 Cognitive Flow Verified.")
    else:
        print("\n❌ v13 Integration Failure: Mission did not reach finality.")

if __name__ == "__main__":
    asyncio.run(test_v13_flow())
