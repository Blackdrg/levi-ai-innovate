import pytest
import json
from unittest.mock import AsyncMock, patch, MagicMock
from backend.services.orchestrator.agents.critic_agent import ValidatorAgent
from backend.services.orchestrator.executor import execute_plan
from backend.services.orchestrator.orchestrator_types import ExecutionPlan, PlanStep
from backend.services.orchestrator.brain import LeviBrain

@pytest.mark.asyncio
async def test_validator_agent_scoring():
    """Verify ValidatorAgent returns structured scores."""
    agent = ValidatorAgent()
    mock_llm_res = json.dumps({
        "quality_score": 0.85,
        "critique_items": ["Good depth", "Needs more metaphors"],
        "reasoning": "Strong but slightly dry."
    })
    
    with patch("backend.services.orchestrator.agents.critic_agent._async_call_llm_api", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = mock_llm_res
        
        result = await agent.execute({
            "goal": "Explain the moon",
            "agent_output": "The moon is a satellite."
        }, {"request_id": "test"})
        
        assert result["success"] is True
        assert result["data"]["quality_score"] == 0.85
        assert "Good depth" in result["data"]["critique"]

@pytest.mark.asyncio
async def test_executor_reflection_trigger():
    """Verify Executor triggers reflection on low scores."""
    step = PlanStep(agent="chat_agent", description="Chat")
    plan = ExecutionPlan(intent="chat", steps=[step])
    context = {"input": "test", "complexity": 10, "request_id": "test"}
    
    # Tool results
    initial_res = {"success": True, "message": "Initial dry response", "agent": "chat_agent"}
    validator_low = {
        "success": False, # Score < 0.7
        "data": {"quality_score": 0.4, "critique": "Too dry and boring."},
        "agent": "critic_agent"
    }
    reflected_res = {"success": True, "message": "Better poetic response", "agent": "chat_agent"}
    
    with patch("backend.services.orchestrator.executor.call_tool", new_callable=AsyncMock) as mock_call:
        # Mock sequence: 1. chat_agent (initial), 2. critic_agent, 3. chat_agent (reflected)
        mock_call.side_effect = [initial_res, validator_low, reflected_res]
        
        results = await execute_plan(plan, context)
        
        assert len(results) == 1 # Only one final result for the step
        assert results[0].message == "Better poetic response"
        assert mock_call.call_count == 3

@pytest.mark.asyncio
async def test_brain_tiered_optimization():
    """Verify Brain applies optimization for Pro users."""
    brain = LeviBrain()
    brain.memory.get_combined_context = AsyncMock(return_value={"user_tier": "pro", "long_term": {}})
    
    # Mock pipe components
    with patch("backend.services.orchestrator.brain.detect_intent", new_callable=AsyncMock) as mock_intent, \
         patch("backend.services.orchestrator.brain.decompose_goal", new_callable=AsyncMock) as mock_decomp, \
         patch("backend.services.orchestrator.brain.execute_plan", new_callable=AsyncMock) as mock_exec, \
         patch("backend.services.orchestrator.brain.synthesize_response", new_callable=AsyncMock) as mock_synth, \
         patch("backend.services.orchestrator.brain.call_tool", new_callable=AsyncMock) as mock_call:
        
        mock_intent.return_value = MagicMock(intent="chat", complexity=8)
        mock_decomp.return_value = MagicMock(overall_strategy="Test")
        mock_exec.return_value = []
        mock_synth.return_value = "Draft Response"
        mock_call.return_value = {"success": True, "data": {"optimized_content": "Optimized Response"}}
        
        res = await brain.route("test input", "user_123", "sess_1")
        
        assert res["response"] == "Optimized Response"
        # Verify optimizer_agent was called
        mock_call.assert_called_with("optimizer_agent", pytest.any, pytest.any)

@pytest.mark.asyncio
async def test_python_repl_piston_and_fallback():
    """Verify PythonREPL handles Piston and Fallback."""
    from backend.services.orchestrator.agents.python_repl_agent import PythonREPLAgent
    agent = PythonREPLAgent()
    
    # 1. Test Piston Success
    mock_piston_res = MagicMock()
    mock_piston_res.json.return_value = {"run": {"code": 0, "output": "4\n"}}
    
    with patch("backend.services.orchestrator.agents.python_repl_agent.async_safe_request", new_callable=AsyncMock) as mock_req:
        mock_req.return_value = mock_piston_res
        
        res = await agent.execute({"code": "print(2+2)"}, {"request_id": "test"})
        assert res["success"] is True
        assert res["data"]["backend"] == "piston"
        assert res["data"]["output"] == "4\n"
        
    # 2. Test Fallback on Piston Error
    with patch("backend.services.orchestrator.agents.python_repl_agent.async_safe_request", side_effect=Exception("Piston DOWN")):
        res = await agent.execute({"code": "print(3+3)"}, {"request_id": "test"})
        assert res["success"] is True
        assert res["data"]["backend"] == "local_fallback"
        assert "6" in res["data"]["output"]
