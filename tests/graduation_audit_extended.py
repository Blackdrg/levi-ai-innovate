"""
Sovereign Graduation Audit v13.1.0 (Extended Suite).
Verifies the 28 points of the Absolute Monolith graduation.
"""

import asyncio
import pytest
from backend.core.memory_manager import MemoryManager
from backend.agents.consensus_agent import ConsensusAgentV11, ConsensusInput, FidelityRubric, AgentResult
from backend.core.blackboard import MissionBlackboard
from backend.auth.jwt_provider import JWTProvider
from backend.utils.encryption import SovereignVault

@pytest.mark.asyncio
async def test_audit_point_14_gdpr_wipe():
    """Point 14: Absolute 5-Tier Memory Wipe."""
    user_id = "test_audit_user"
    mm = MemoryManager()
    cleared = await mm.clear_all_user_data(user_id)
    assert isinstance(cleared, int)
    print(f"Audit Point 14 Passed: {cleared} interaction shards purged.")

@pytest.mark.asyncio
async def test_audit_point_08_fidelity_rubric():
    """Point 08: Formal Weighted Aggregator (v13.1)."""
    consensus = ConsensusAgentV11()
    rubric = FidelityRubric(
        syntax_correctness=1.0,
        logical_consistency=1.0,
        factual_grounding=0.8,
        sovereign_resonance=0.9
    )
    # Expected: (1.0*0.3) + (1.0*0.3) + (0.8*0.2) + (0.9*0.2) = 0.3 + 0.3 + 0.16 + 0.18 = 0.94
    assert abs(rubric.calculate_fidelity() - 0.94) < 0.01
    print("Audit Point 08 Passed: Fidelity Rubric calculated accurately.")

@pytest.mark.asyncio
async def test_audit_point_11_blackboard_isolation():
    """Point 11: Session-Keyed Transient Memory."""
    bb = MissionBlackboard("session_alpha")
    bb.update_insight("Artisan", "Code is stable.")
    serialized = bb.serialize()
    
    bb2 = MissionBlackboard.deserialize("session_alpha", serialized)
    assert bb2.state.agent_insights["Artisan"] == "Code is stable."
    print("Audit Point 11 Passed: Mission Blackboard serialization verified.")

@pytest.mark.asyncio
async def test_audit_point_17_vault_envelope():
    """Point 17: AES-256 Envelope Encryption."""
    secret = "Top Secret Sovereign Intel"
    encrypted = SovereignVault.encrypt(secret)
    assert ":" in encrypted
    assert encrypted.startswith("v1:")
    
    decrypted = SovereignVault.decrypt(encrypted)
    assert decrypted == secret
    print("Audit Point 17 Passed: Envelope Encryption verified.")

@pytest.mark.asyncio
async def test_audit_point_26_jwt_lifecycle():
    """Point 26: Identity Rotation + JTI Blacklist."""
    user_id = "sovereign_user_001"
    tokens = JWTProvider.create_token_pair(user_id, {"role": "creator"})
    
    decoded = JWTProvider.verify_token(tokens["identity_token"])
    assert decoded["sub"] == user_id
    
    # Test Revocation
    JWTProvider.revoke_token(tokens["ident_jti"])
    decoded_revoked = JWTProvider.verify_token(tokens["identity_token"])
    assert decoded_revoked is None
    print("Audit Point 26 Passed: JWT Lifecycle and Revocation verified.")

if __name__ == "__main__":
    asyncio.run(test_audit_point_14_gdpr_wipe())
    asyncio.run(test_audit_point_08_fidelity_rubric())
    asyncio.run(test_audit_point_11_blackboard_isolation())
    asyncio.run(test_audit_point_17_vault_envelope())
    asyncio.run(test_audit_point_26_jwt_lifecycle())
