import asyncio
import logging
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from backend.core.v8.decision_engine import DecisionEngine
from backend.core.v8.llm_guard import LLMGuard
from backend.core.v8.rules_engine import RulesEngine
from backend.core.orchestrator_types import IntentResult

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("VerifyV8.12")

async def test_decision_engine():
    logger.info("--- Testing Decision Engine ---")
    engine = DecisionEngine()
    
    # Mock Memory Manager
    class MockMemory:
        async def get_combined_context(self, *args):
            return {"graph_resonance": [], "long_term": {}}
            
    memory = MockMemory()
    
    test_cases = [
        ("Hello there", IntentResult(intent_type="greeting", confidence_score=0.9), "INTERNAL"),
        ("Calculate 2+2", IntentResult(intent_type="math", confidence_score=0.8), "ENGINE"),
        ("Write a python script", IntentResult(intent_type="code", confidence_score=0.8), "ENGINE"),
        ("What is the meaning of life?", IntentResult(intent_type="chat", confidence_score=0.5), "LLM"),
    ]
    
    for text, intent, expected in test_cases:
        metrics = await engine.compute_metrics(text, intent, memory, "user_1", "sess_1")
        decision = engine.decide(metrics)
        logger.info(f"Input: '{text}' -> Decision: {decision} (Expected: {expected})")
        assert decision == expected, f"Failed on '{text}': got {decision}"

async def test_llm_guard():
    logger.info("--- Testing LLM Guard ---")
    guard = LLMGuard()
    
    test_cases = [
        ({"internal_conf": 0.8, "engine_capable": False, "memory_match": 0}, False), # INTERNAL
        ({"internal_conf": 0.4, "engine_capable": True, "memory_match": 0}, False), # ENGINE
        ({"internal_conf": 0.4, "engine_capable": False, "memory_match": 0.8}, False), # MEMORY
        ({"internal_conf": 0.4, "engine_capable": False, "memory_match": 0.1}, True), # LLM ALLOWED
    ]
    
    for metrics, expected in test_cases:
        allowed = guard.allow_llm("test task", metrics)
        logger.info(f"Metrics: {metrics} -> Allowed: {allowed} (Expected: {expected})")
        assert allowed == expected

async def test_rules_engine():
    logger.info("--- Testing Rules Engine ---")
    rules = RulesEngine()
    
    task = "repeat after me: levi is the brain"
    solution = "LEVI IS THE BRAIN"
    
    rules.create_rule(task, solution)
    cached = rules.get_rule(task)
    logger.info(f"Rule for '{task}': {cached}")
    assert cached == solution

async def main():
    try:
        await test_decision_engine()
        await test_llm_guard()
        await test_rules_engine()
        logger.info("\n✅ ALL BRAIN-FIRST ARCHITECTURAL TESTS PASSED (v8.12)")
    except Exception as e:
        logger.error(f"\n❌ VERIFICATION FAILED: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
