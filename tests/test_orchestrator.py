import asyncio
import os
import sys
from unittest.mock import MagicMock

# Add project root to path
sys.path.append(os.getcwd())

# Mock environment variables
os.environ["GROQ_API_KEY"] = "mock_key"
os.environ["TOGETHER_API_KEY"] = "mock_key"

async def test_orchestrator():
    from backend.services.orchestrator.engine import run_orchestrator
    
    print("--- Testing Simple Chat ---")
    resp = await run_orchestrator(
        user_input="Hello LEVI, what is the meaning of life?",
        session_id="test_session",
        user_id="test_user",
        user_tier="free"
    )
    print(f"Response: {resp}\n")

    print("--- Testing Multi-Step Research & Image ---")
    # This might fail if LLM calls aren't mocked, but let's see what happens 
    # or how it handles the plan.
    resp = await run_orchestrator(
        user_input="Research the latest AI trends and then draw a futuristic city representing them.",
        session_id="test_session_multi",
        user_id="test_user",
        user_tier="pro"
    )
    print(f"Response: {resp}\n")

if __name__ == "__main__":
    asyncio.run(test_orchestrator())
