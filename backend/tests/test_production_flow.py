"""
backend/tests/test_production_flow.py

Final production verification for Phase 8: Production Polish & Real-Time Feedback.
"""

import pytest
from backend.services.orchestrator.brain import LeviBrain

@pytest.mark.asyncio
async def test_full_agentic_workflow_with_status():
    """
    Test a complex query that triggers multiple agents and reports status.
    """
    brain = LeviBrain()
    status_updates = []

    async def _status_cb(msg: str):
        status_updates.append(msg)

    # Complex query: Research + Calculation
    user_input = "Search for the current price of Gold and calculate how much 50 grams is worth."
    
    result = await brain.route(
        user_input=user_input,
        user_id="test_prod_user",
        session_id="test_prod_sess",
        status_callback=_status_cb
    )

    # 1. Verify Status Callbacks
    assert len(status_updates) > 0
    assert any("Analyzing" in s for s in status_updates)
    assert any("Constructing" in s for s in status_updates)
    assert any("Executing" in s for s in status_updates)

    # 2. Verify Intent & Plan
    assert result["intent"] in ("research", "logic", "complex")
    agent_names = [r["agent"] for r in result["results"]]
    assert "search_agent" in agent_names
    assert "python_repl_agent" in agent_names

    # 3. Verify Synthesis
    assert "Gold" in result["response"]
    assert any(char.isdigit() for char in result["response"]) # Should contain calculated numbers

@pytest.mark.asyncio
async def test_studio_agent_initiation():
    """
    Verify that image_agent correctly triggers a studio job.
    """
    brain = LeviBrain()
    user_input = "Create a cinematic image of a lone philosopher in a neon library."
    
    result = await brain.route(
        user_input=user_input,
        user_id="test_studio_user",
        session_id="test_studio_sess"
    )

    # Verify agent execution
    agent_names = [r["agent"] for r in result["results"]]
    assert "image_agent" in agent_names
    
    # Verify Job ID in response and data
    assert "Job ID:" in result["response"]
    
    image_result = next(r for r in result["results"] if r["agent"] == "image_agent")
    assert "job_id" in image_result["data"]
    assert image_result["data"]["type"] == "image"

@pytest.mark.asyncio
async def test_error_resilience_in_pipeline():
    """
    Verify that the pipeline handles tool failures gracefully.
    """
    from backend.services.orchestrator.orchestrator_types import ExecutionPlan, PlanStep
    from backend.services.orchestrator.executor import execute_plan
    
    # Plan with a failing step
    plan = ExecutionPlan(
        intent="fault_test",
        steps=[
            PlanStep(
                description="Failing Step",
                agent="python_repl_agent",
                tool_input={"code": "raise Exception('Intentional Failure')"},
                critical=False # Allow continuation
            ),
            PlanStep(
                description="Recovery Step",
                agent="local_agent",
                tool_input={"input": "I recovered."},
                critical=True
            )
        ]
    )
    
    context = {"input": "Test error", "user_id": "tester"}
    results = await execute_plan(plan, context)
    
    assert len(results) == 2
    assert results[0].success is False
    assert results[1].success is True
    assert "recovered" in results[1].message
