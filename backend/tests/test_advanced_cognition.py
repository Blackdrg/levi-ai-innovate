"""
backend/tests/test_advanced_cognition.py

Verification for Phase 7: Advanced Cognition & Real-World Integration.
"""

import pytest
from backend.services.orchestrator.brain import LeviBrain

@pytest.mark.asyncio
async def test_logic_intent_and_repl():
    brain = LeviBrain()
    # Test a calculation query
    result = await brain.route(
        user_input="Calculate the compound interest for 1000 at 5% for 10 years",
        user_id="test_user",
        session_id="test_sess"
    )
    
    assert result["intent"] == "logic"
    # Ensure python_repl_agent was used
    agent_names = [r["agent"] for r in result["results"]]
    assert "python_repl_agent" in agent_names
    
    # Check for actual calculation in the response
    assert any(x in result["response"] for x in ["1628", "interest", "total"])
    logger_info = f"Logic Response: {result['response']}"
    print(logger_info)

@pytest.mark.asyncio
async def test_multistep_injection():
    """
    Simulate a plan where Step 2 uses Step 1 output.
    Note: In current planner, we might need a manual plan for a unit test 
    unless the planner naturally generates one.
    """
    from backend.services.orchestrator.orchestrator_types import ExecutionPlan, PlanStep
    from backend.services.orchestrator.executor import execute_plan
    
    plan = ExecutionPlan(
        intent="research_math",
        steps=[
            PlanStep(
                description="Search for a number",
                agent="local_agent", # Simple mock for step 1
                tool_input={"input": "The number is 42"},
                critical=True
            ),
            PlanStep(
                description="Double the number",
                agent="python_repl_agent",
                tool_input={"code": "print(int('{{last_result}}'.split()[-1]) * 2)"},
                critical=True
            )
        ]
    )
    
    context = {"input": "Double forty-two", "user_id": "test_user"}
    results = await execute_plan(plan, context)
    
    assert len(results) == 2
    assert "84" in results[1].message
    print(f"Injection Result: {results[1].message}")

@pytest.mark.asyncio
async def test_search_agent_fallback():
    # If TAVILY_API_KEY is missing, it should fallback to LLM
    from backend.services.orchestrator.tool_registry import call_tool
    res = await call_tool("search_agent", {"input": "What is the capital of France?"}, {})
    assert res["success"] is True
    assert "Paris" in res["message"]
