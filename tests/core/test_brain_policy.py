import asyncio
import logging
import sys
import os

# Add backend to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from backend.core.policy_engine import BrainPolicyEngine
from backend.core.orchestrator_types import IntentResult, BrainMode

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TestBrainV14")

async def test_policy_engine():
    engine = BrainPolicyEngine()
    
    # Test 1: Fast Path
    fast_intent = IntentResult(intent_type="chat", complexity_level=1, confidence_score=0.99)
    decision = await engine.decide("hi", fast_intent)
    logger.info(f"TEST Fast Path: Mode={decision.mode}")
    assert decision.mode == BrainMode.FAST
    assert decision.execution_policy.parallel_waves == 1
    
    # Test 2: Deep Reasoning
    deep_intent = IntentResult(intent_type="chat", complexity_level=3, confidence_score=0.95)
    decision = await engine.decide("explain quantum entanglement in detail", deep_intent)
    logger.info(f"TEST Deep Reasoning: Mode={decision.mode}")
    assert decision.mode == BrainMode.DEEP
    assert decision.enable_agents["critic"] == True
    
    # Test 3: Research Mode
    research_intent = IntentResult(intent_type="search", complexity_level=2, confidence_score=0.9)
    decision = await engine.decide("search for latest AI news", research_intent)
    logger.info(f"TEST Research Mode: Mode={decision.mode}")
    assert decision.mode == BrainMode.RESEARCH
    assert decision.enable_agents["browser"] == True
    assert decision.memory_policy.neo4j == True
    
    # Test 4: Secure Mode
    secure_intent = IntentResult(intent_type="chat", complexity_level=1, confidence_score=0.99, is_sensitive=True)
    decision = await engine.decide("my password is...", secure_intent)
    logger.info(f"TEST Secure Mode: Mode={decision.mode}")
    assert decision.mode == BrainMode.SECURE
    assert decision.execution_policy.sandbox_required == True
    assert decision.llm_policy.local_only == True

    logger.info("✅ All Policy Engine tests passed!")

if __name__ == "__main__":
    asyncio.run(test_policy_engine())
