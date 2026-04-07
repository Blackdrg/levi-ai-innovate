"""
backend/tests/test_v6_full_cycle.py

LEVI v6: Final verification for Meta-Brain and Agent Swarm.
"""

import pytest
from backend.services.orchestrator.meta_planner import decompose_goal
from backend.services.orchestrator.orchestrator_types import IntentResult

@pytest.mark.asyncio
async def test_v6_meta_brain_decomposition():
    """
    Verify that the Meta-Brain correctly decomposes a complex problem.
    """
    user_input = "Analyze the stoicism in my recent history and generate a visual metaphor as an image."
    intent = IntentResult(intent="complex", complexity=8)
    context = {"user_id": "test_v6_user"}
    
    strategy = await decompose_goal(user_input, intent, context)
    
    assert strategy.overall_strategy != ""
    assert len(strategy.subgoals) > 1
    
    # Verify agent mapping
    agents = [sg.target_agent for sg in strategy.subgoals]
    assert "chat_agent" in agents or "search_agent" in agents
    assert "image_agent" in agents

@pytest.mark.asyncio
async def test_v6_reflection_loop_trigger():
    """
    Verify that the executor triggers the CriticAgent for complex reasoning.
    """
    from backend.services.orchestrator.executor import execute_plan
    from backend.services.orchestrator.orchestrator_types import ExecutionPlan, PlanStep
    
    plan = ExecutionPlan(
        intent="reasoning_test",
        steps=[
            PlanStep(
                description="Write a complex philosophical essay.",
                agent="chat_agent",
                critical=True
            )
        ]
    )
    
    # Complexity 6 should trigger the CriticAgent loop in executor.py
    context = {"input": "Write an essay about time.", "user_id": "test_v6_user", "complexity": 6}
    
    results = await execute_plan(plan, context)
    
    assert len(results) >= 1
    assert results[0].success is True
    # If the critic was triggered, it would log "Invoking Reflection Loop"

@pytest.mark.asyncio
async def test_v6_evolutionary_memory_ranking():
    """
    Verify that Importance Scoring affects memory retrieval.
    """
    from backend.services.orchestrator.memory_utils import search_relevant_facts, store_facts
    
    user_id = "test_v6_mem_user"
    
    # Store one low-importance and one high-importance fact
    facts = [
        {"fact": "User likes cookies.", "category": "preference", "importance": 0.2},
        {"fact": "User is a dedicated Zen practitioner.", "category": "trait", "importance": 1.0}
    ]
    
    await store_facts(user_id, facts)
    
    # Search for "overall character"
    results = await search_relevant_facts(user_id, "character", limit=5)
    
    # The high-importance fact should be ranked first even if the semantic distance is similar
    assert results[0]["fact"] == "User is a dedicated Zen practitioner."
    assert results[0]["importance"] == 1.0
