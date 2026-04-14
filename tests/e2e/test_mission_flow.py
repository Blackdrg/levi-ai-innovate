import sys
import os
import pytest
import asyncio

# Ensure project root is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from backend.core.orchestrator import Orchestrator

@pytest.mark.asyncio
async def test_mission_flow_e2e():
    """
    Phase 0.6: E2E Mission Flow Verification.
    mission input -> output verification
    """
    orchestrator = Orchestrator()
    # Initialize components if needed
    # await orchestrator.initialize() 

    user_input = "Write a python script to calculate fibonacci numbers"
    user_id = "test_user"
    session_id = "test_session"

    # Phase 0.1: Implementation of run_mission
    result = await orchestrator.run_mission(user_input, user_id, session_id)

    assert "response" in result
    assert result["status"] == "success"
    assert "mission_id" in result
    assert len(result["response"]) > 0
    
    print(f"\nMission Result: {result['response'][:100]}...")
