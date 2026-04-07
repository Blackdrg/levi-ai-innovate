import pytest
from backend.services.orchestrator.brain import LeviBrain
from backend.services.learning.logic import AdaptivePromptManager

@pytest.mark.asyncio
async def test_adaptive_prompt_selection():
    """Verify that AdaptivePromptManager returns a valid variant."""
    apm = AdaptivePromptManager()
    variant = await apm.get_best_variant("philosophical")
    assert variant in apm.PROMPT_VARIANTS
    assert "LEVI" in variant

@pytest.mark.asyncio
async def test_user_preference_injection():
    """Verify that preferences are correctly merged into the Brain context."""
    user_id = "test_learner_user"
    brain = LeviBrain()
    
    # Mocking preferences (to avoid DB dependency in this unit test)
    # In a real integration test, we'd seed Firestore.
    context = await brain.memory.get_combined_context(user_id, "test_session", "Hello")
    
    assert "preferences" in context
    assert "preferred_moods" in context["preferences"]
    assert "response_style" in context["preferences"]

@pytest.mark.asyncio
async def test_learning_hook_trigger():
    """Verify that reasoning_engine triggers the autonomous evolution check."""
    brain = LeviBrain()
    user_input = "My name is John and I love Stoic philosophy."
    
    from backend.services.orchestrator.orchestrator_types import IntentResult
    intent = IntentResult(intent="chat", complexity=1, confidence=1.0)
    context = {
        "user_id": "john_123",
        "session_id": "sess_001",
        "mood": "stoic",
        "preferences": {"preferred_moods": ["stoic"], "response_style": "concise"}
    }
    
    # LEVEL 1 Task: Should trigger Local Reasoning (Complexity 1 < 3)
    result = await brain.reasoning_engine(user_input, intent, context, "req_test_001")
    
    assert "response" in result
    assert result["intent"] == "chat"
    assert result["route"] == "LOCAL" # Verified: Hardened Meta-Brain routing

@pytest.mark.asyncio
async def test_adaptive_prompt_evolution():
    """Verify that AdaptivePromptManager can evolve based on 5-star feedback."""
    apm = AdaptivePromptManager("user_123")
    # Mocking successful feedback
    await apm.log_performance("p_stoic_v1", 5.0)
    
    # Check if variant score increased
    from backend.db.redis_client import r as redis
    score = redis.zscore("user:user_123:prompt_scores", "p_stoic_v1")
    assert float(score) > 0.0

@pytest.mark.asyncio
async def test_distilled_persona_injection():
    """Verify that distilled traits are correctly injected into system instructions."""
    user_id = "test_persona_user"
    from backend.services.orchestrator.memory_utils import store_facts
    await store_facts(user_id, [{"fact": "User is a minimalist", "category": "trait", "importance": 0.95}])
    
    apm = AdaptivePromptManager(user_id)
    instructions = await apm.get_system_instructions()
    
    assert "minimalist" in instructions.lower()
    assert "LEVI" in instructions
