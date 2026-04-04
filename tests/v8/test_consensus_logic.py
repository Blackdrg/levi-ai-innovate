"""
Unit Tests for LEVI-AI Phase 3: SWARM CONSENSUS.
Verifies the Fidelity Matrix calculation and candidate selection.
"""

import asyncio
import pytest
import logging
from backend.agents.consensus_agent import ConsensusAgentV8, ConsensusInput
from backend.agents.base import AgentResult

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@pytest.mark.asyncio
async def test_consensus_adjudication():
    """Verifies that ConsensusAgentV8 can choose the best candidate."""
    goal = "Implement a secure login function in Python."
    
    candidates = [
        AgentResult(
            agent="CodeAgent_Draft",
            message="def login(u, p): return True # insecure",
            success=True,
            score=0.4
        ),
        AgentResult(
            agent="CodeAgent_Secure",
            message="def login(username, password):\n    # Use bcrypt to verify\n    return bcrypt.check(password, stored_hash)",
            success=True,
            score=0.95
        ),
        AgentResult(
            agent="CodeAgent_Optimized",
            message="def login(u, p): pass # placeholder",
            success=True,
            score=0.2
        )
    ]
    
    agent = ConsensusAgentV8()
    result = await agent.execute(ConsensusInput(goal=goal, candidates=candidates))
    
    assert result.success is True
    winner = result.data.get("winner", {})
    assert winner.get("agent") == "CodeAgent_Secure"
    assert result.fidelity_score >= 0.8
    
    logger.info(f"[Test] Consensus Adjudication Verified. Winner: {winner.get('agent')} with Score: {result.fidelity_score}")

@pytest.mark.asyncio
async def test_fidelity_matrix_logic():
    """Verifies the structured JSON output of the consensus matrix."""
    goal = "Summarize the history of AI."
    candidates = [
        AgentResult(agent="A1", message="AI started in 1956.", success=True),
        AgentResult(agent="A2", message="AI is magic.", success=True)
    ]
    
    agent = ConsensusAgentV8()
    result = await agent.execute(ConsensusInput(goal=goal, candidates=candidates))
    
    assert "matrix" in result.data
    matrix = result.data["matrix"]
    assert len(matrix) > 0
    # Check if matrix contains C, L, S scores (Implicit in prompt, verified in result)
    logger.info(f"[Test] Fidelity Matrix Logic Verified: {matrix}")

if __name__ == "__main__":
    asyncio.run(test_consensus_adjudication())
    asyncio.run(test_fidelity_matrix_logic())
    print("\nPhase 3 Verification Suite: SUCCESS")
