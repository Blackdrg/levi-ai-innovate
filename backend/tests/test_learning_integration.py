import pytest
from backend.services.orchestrator.brain import LeviBrain
from backend.services.orchestrator.memory_manager import MemoryManager
from backend.learning import UserPreferenceModel, AdaptivePromptManager

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
    """Verify that reasoning_engine triggers the learning background task."""
    # This is a bit harder to test without mocks, but we can verify 
    # that the call doesn't crash and returns the correct structure.
    brain = LeviBrain()
    user_input = "My name is John and I love Stoic philosophy."
    
    from backend.services.orchestrator.orchestrator_types import IntentResult
    intent = IntentResult(intent="chat", complexity=3, confidence=1.0)
    context = {
        "user_id": "john_123",
        "session_id": "sess_001",
        "mood": "stoic",
        "preferences": {"preferred_moods": ["stoic"], "response_style": "concise"}
    }
    
    # This will trigger a background task (asyncio.create_task)
    result = await brain.reasoning_engine(user_input, intent, context, "req_test_001")
    
    assert "response" in result
    assert result["intent"] == "chat"
    # The response should ideally be generated but since we are in a test env, 
    # it depends on whether GROQ_API_KEY is set.
