import pytest
import asyncio
from backend.core.v8.learning import FragilityTracker
from backend.core.v8.goal_engine import GoalEngine
from backend.core.v8.critic import ReflectionEngine
from backend.memory.cache import MemoryCache

@pytest.mark.asyncio
async def test_fragility_tracking():
    user_id = "test_user_evolution"
    domain = "code"
    
    # Reset state
    MemoryCache.delete(f"fragility:{user_id}:{domain}")
    
    # 1. Start with 0 fragility
    assert FragilityTracker.get_fragility(user_id, domain) == 0.0
    
    # 2. Record failures
    FragilityTracker.record_outcome(user_id, domain, success=False)
    assert FragilityTracker.get_fragility(user_id, domain) == 0.4
    
    FragilityTracker.record_outcome(user_id, domain, success=False)
    assert FragilityTracker.get_fragility(user_id, domain) == 0.8
    
    # 3. Verify Moderate Decay (Success resets streak)
    FragilityTracker.record_outcome(user_id, domain, success=True)
    FragilityTracker.record_outcome(user_id, domain, success=True)
    # Still fragile until streak >= 3
    assert FragilityTracker.get_fragility(user_id, domain) == 0.8
    
    FragilityTracker.record_outcome(user_id, domain, success=True)
    assert FragilityTracker.get_fragility(user_id, domain) == 0.0

@pytest.mark.asyncio
async def test_evolutionary_goal_weighting():
    user_id = "test_user_evolution_goal"
    engine = GoalEngine()
    
    # 1. Baseline Perfection
    perception = {
        "user_id": user_id,
        "input": "Write a complex rust function",
        "intent": type('Intent', (), {'intent_type': 'code', 'complexity_level': 4})(),
        "context": {"long_term": {"traits": []}}
    }
    
    MemoryCache.delete(f"fragility:{user_id}:code")
    goal = await engine.create_goal(perception)
    # Complexity 4 -> Base SC weight ~ 0.7
    assert 0.6 < goal.self_correction_weight <= 0.8
    
    # 2. Record fragility
    FragilityTracker.record_outcome(user_id, "code", success=False)
    FragilityTracker.record_outcome(user_id, "code", success=False)
    
    goal_fragile = await engine.create_goal(perception)
    # Weight should increase due to fragility 0.8
    assert goal_fragile.self_correction_weight > goal.self_correction_weight
    assert goal_fragile.self_correction_weight >= 0.9

@pytest.mark.asyncio
async def test_reflection_thresholding():
    engine = ReflectionEngine()
    
    class MockGoal:
        def __init__(self, weight):
            self.self_correction_weight = weight
            self.objective = "Test objective"
            self.success_criteria = ["Criterion 1"]
            
    perception = {"input": "test", "context": {}}
    
    # 1. Low Weight -> Low Threshold
    goal_low = MockGoal(0.2)
    # We mock call_tool to avoid real LLM calls
    import backend.core.v8.critic
    original_call_tool = backend.core.v8.critic.call_tool
    
    async def mock_call(tool, params, ctx):
        return {"data": {"quality_score": 0.82, "hallucination_detected": False}}
        
    backend.core.v8.critic.call_tool = mock_call
    
    eval_low = await engine.evaluate("response", goal_low, perception)
    # Threshold should be ~ 0.83, so 0.82 is NOT satisfactory
    assert eval_low["threshold"] < 0.85
    
    # 2. High Weight -> High Threshold
    goal_high = MockGoal(0.9)
    eval_high = await engine.evaluate("response", goal_high, perception)
    # Threshold should be ~ 0.935
    assert eval_high["threshold"] > 0.9
    assert not eval_high["is_satisfactory"] # 0.82 < 0.935
    
    backend.core.v8.critic.call_tool = original_call_tool

if __name__ == "__main__":
    asyncio.run(test_fragility_tracking())
    asyncio.run(test_evolutionary_goal_weighting())
    print("Evolutionary Tests Passed Locally.")
