import pytest
import json
from unittest.mock import AsyncMock, patch, MagicMock
from backend.services.orchestrator.executor import _execute_step_with_resilience
from backend.services.orchestrator.orchestrator_types import PlanStep, ToolResult
from backend.services.orchestrator.meta_planner import decompose_goal
from backend.services.orchestrator.memory_manager import MemoryManager

@pytest.mark.asyncio
async def test_reflex_ledger_logging():
    """Verify tool failures are logged to the Reflex Ledger."""
    step = PlanStep(agent="image_agent", description="Generate image")
    context = {"user_tier": "pro", "request_id": "test_reflex"}
    
    # Mock a tool failure
    fail_res = ToolResult(success=False, message="API Down", error="ConnectionTimeout: Failed to connect", agent="image_agent")
    
    with patch("backend.services.orchestrator.executor.call_tool", new_callable=AsyncMock) as mock_call, \
         patch("backend.redis_client.HAS_REDIS", True), \
         patch("backend.redis_client.r") as mock_redis:
        
        mock_call.return_value = fail_res
        
        await _execute_step_with_resilience(step, context)
        
        # Verify ledger incremented
        mock_redis.hincrby.assert_any_call("ledger:agent:image_agent", "failure_calls", 1)
        mock_redis.hincrby.assert_any_call("ledger:agent:image_agent:patterns", "ConnectionTimeout", 1)

@pytest.mark.asyncio
async def test_adaptive_planning_advisory():
    """Verify Meta-Brain receives performance advisory in prompt."""
    from backend.services.orchestrator.orchestrator_types import IntentResult
    intent = IntentResult(intent="image", complexity=5)
    
    # Mock Redis returning high failure stats for image_agent
    with patch("backend.redis_client.HAS_REDIS", True), \
         patch("backend.redis_client.r") as mock_redis, \
         patch("backend.services.orchestrator.meta_planner._async_call_llm_api", new_callable=AsyncMock) as mock_llm:
        
        # stats for image_agent: 10 calls, 5 failures (50%)
        mock_redis.hgetall.return_value = {b"total_calls": b"10", b"failure_calls": b"5"}
        mock_llm.return_value = json.dumps({
            "overall_strategy": "Avoiding image agent due to instability.",
            "recommended_model": "llama-3.1-8b-instant",
            "subgoals": [{"description": "Describe image instead", "target_agent": "chat_agent"}]
        })
        
        strategy = await decompose_goal("Generate a sunset", intent, {})
        
        # Check LLM call includes advisory
        args, kwargs = mock_llm.call_args
        system_prompt = kwargs['messages'][0]['content']
        assert "[SYSTEM ADVISORY]: image_agent is unstable" in system_prompt

@pytest.mark.asyncio
async def test_silent_distillation_trigger():
    """Verify memory distillation triggers after enough interactions."""
    with patch("backend.redis_client.HAS_REDIS", True), \
         patch("backend.redis_client.r") as mock_redis, \
         patch("backend.services.orchestrator.memory_manager.MemoryManager.distill_core_memory", new_callable=AsyncMock) as mock_distill, \
         patch("backend.services.orchestrator.memory_manager.extract_facts", new_callable=AsyncMock) as mock_extract, \
         patch("backend.services.orchestrator.memory_manager.store_facts", new_callable=AsyncMock) as mock_store:
        
        mock_extract.return_value = [{"fact": "Test", "category": "preference"}]
        # Mock counter hitting 20
        mock_redis.incr.return_value = 20
        
        await MemoryManager.process_new_interaction("user_123", "hi", "hello")
        
        # Verify distillation triggered
        mock_distill.assert_called_once_with("user_123")
        mock_redis.set.assert_called_with("user:user_123:opts:distill_count", 0)
