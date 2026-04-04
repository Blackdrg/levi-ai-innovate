import asyncio
import json
import uuid
from unittest.mock import MagicMock, patch

# Mocking backend components before import if necessary
import sys
from types import ModuleType

# Mock redis for testing
mock_redis = MagicMock()
sys.modules['redis'] = MagicMock()
sys.modules['redis'].Redis.return_value = mock_redis

from backend.agents.base import SovereignAgent, AgentResult, AgentState
from backend.services.agent_bus import AgentBus
from backend.agents.consensus_agent import ConsensusAgentV11, ConsensusInput
from backend.core.orchestrator_types import ToolResult

class MockAgent(SovereignAgent):
    async def _run(self, input_data: any, lang: str = "en", **kwargs):
        return {"message": "Success", "score": 0.9}

async def test_agent_state():
    print("Testing Agent State...")
    agent = MockAgent("TestAgent")
    assert isinstance(agent.state, AgentState)
    assert agent.state.strategy == "optimize"
    print("Agent State: OK")

async def test_agent_bus():
    print("Testing Agent Bus (Redis-backed)...")
    bus = AgentBus()
    
    # Mock Redis methods
    mock_redis.lpush = MagicMock()
    mock_redis.brpop = MagicMock(return_value=(b"queue", json.dumps({"test": "data"}).encode()))
    
    await bus.send("target", {"hello": "world"})
    mock_redis.lpush.assert_called_once()
    
    msg = await bus.receive("me")
    assert msg == {"test": "data"}
    print("Agent Bus: OK")

async def test_consensus_formula():
    print("Testing Consensus Formula...")
    agent = ConsensusAgentV11()
    
    candidates = [
        AgentResult(agent="AgentA", message="Output A", fidelity_score=0.9, confidence=0.8),
        AgentResult(agent="AgentB", message="Output B", fidelity_score=0.7, confidence=0.9)
    ]
    
    input_data = ConsensusInput(goal="Test goal", candidates=candidates)
    
    # Mock LLM generator
    with patch("backend.agents.consensus_agent.SovereignGenerator") as mock_gen:
        mock_instance = mock_gen.return_value
        mock_instance.council_of_models = asyncio.Future()
        mock_instance.council_of_models.set_result(json.dumps({
            "winner_index": 0,
            "fidelity_score": 0.95,
            "collective_resonance": 0.9,
            "justification": "Better correctness",
            "scores": [
                {"index": 0, "correctness": 0.95, "confidence": 0.8, "agreement": 0.7},
                {"index": 1, "correctness": 0.7, "confidence": 0.9, "agreement": 0.7}
            ]
        }))
        
        result = await agent._run(input_data)
        
        # Verify formula: (correctness * 0.5 + confidence * 0.3 + agreement * 0.2)
        # AgentA score: (0.95 * 0.5 + 0.8 * 0.3 + 0.7 * 0.2) = 0.475 + 0.24 + 0.14 = 0.855
        # AgentB score: (0.7 * 0.5 + 0.9 * 0.3 + 0.7 * 0.2) = 0.35 + 0.27 + 0.14 = 0.76
        
        print(f"Final Scores: {result['data']['final_scores']}")
        assert result['data']['final_scores'][0] > result['data']['final_scores'][1]
        assert result['data']['winner']['agent'] == "AgentA"
        print("Consensus Formula: OK")

async def main():
    await test_agent_state()
    await test_agent_bus()
    await test_consensus_formula()
    print("\nALL PHASE 2 VERIFICATIONS PASSED!")

if __name__ == "__main__":
    asyncio.run(main())
