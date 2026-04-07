import asyncio
import logging
from backend.core.v8.brain import LeviBrainCoreController

# Setup basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_levi_brain_controller():
    controller = LeviBrainCoreController()
    
    test_cases = [
        {
            "name": "Level 1: Greeting",
            "input": "Hello LEVI",
            "expected_level": 1
        },
        {
            "name": "Level 2: Math",
            "input": "Calculate 50 * 12",
            "expected_level": 2
        },
        {
            "name": "Level 4: Complex Synthesis",
            "input": "Write a story about a sentient AI and a forgotten satellite.",
            "expected_level": 4
        }
    ]
    
    print("\n--- [LeviBrain Core Controller Verification] ---")
    
    for case in test_cases:
        print(f"\nTesting Case: {case['name']}")
        print(f"Input: {case['input']}")
        
        # We need to mock user_id and session_id
        res = await controller.run(case["input"], user_id="test_user", session_id="test_session")
        
        actual_level = res.get("reasoning_level")
        print(f"Detected Reasoning Level: {actual_level}")
        
        if actual_level == case["expected_level"]:
            print("✅ SUCCESS: Correct priority level identified.")
        else:
            print(f"❌ FAILURE: Expected level {case['expected_level']}, got {actual_level}")
            
        print(f"Response: {res.get('response')[:100]}...")

if __name__ == "__main__":
    asyncio.run(test_levi_brain_controller())
