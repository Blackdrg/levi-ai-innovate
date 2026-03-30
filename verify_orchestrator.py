import asyncio
import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

from backend.services.orchestrator.engine import run_orchestrator

async def test_orchestrator():
    test_cases = [
        "Hello LEVI, how are you today?", # Chat
        "Generate a futuristic city image with neon lights.", # Image
        "Write a python script to calculate Fibonacci numbers.", # Code
        "Search for the latest breakthroughs in fusion energy." # Search
    ]

    for i, text in enumerate(test_cases):
        print(f"\n--- Test Case {i+1}: '{text}' ---")
        try:
            response = await run_orchestrator(
                user_input=text,
                session_id="test_session",
                user_id="test_user",
                user_tier="pro"
            )
            print(f"RESPONSE:\n{response[:300]}...")
        except Exception as e:
            print(f"ERROR: {e}")

if __name__ == "__main__":
    asyncio.run(test_orchestrator())
