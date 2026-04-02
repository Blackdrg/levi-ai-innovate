import asyncio
import uuid
import sys
import os

# Add the project root to sys.path for backend imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from backend.core.brain import LeviBrainV8

async def test_brain_v8():
    print("--- [LeviBrain v8] Phase 6: Verifying Cognitive Pipeline ---")
    
    brain = LeviBrainV8()
    user_id = "test_user_v8"
    session_id = str(uuid.uuid4())
    user_input = "Explain the relationship between the observer and the observed in quantum mechanics."

    print(f"User Input: {user_input}")
    print("Initiating 7-step cognitive sequence...")

    async for chunk in brain.stream(user_input, user_id, session_id):
        event = chunk.get("event")
        data = chunk.get("data")
        
        if event == "activity":
            print(f" [ACTIVITY] {data}")
        elif event == "graph":
            print(f" [PLAN] Generated {len(data.get('nodes', []))} task nodes.")
        elif event == "results":
            print(f" [EXECUTION] Processed {len(data)} results.")
        elif event == "choice":
            # Token streaming
            pass

    print("\n--- Mission Complete ---")

if __name__ == "__main__":
    asyncio.run(test_brain_v8())
