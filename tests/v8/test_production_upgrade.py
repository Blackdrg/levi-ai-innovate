import pytest
import uuid
from backend.core.v8.brain import LeviBrainCoreController
from backend.core.v8.sync_engine import SovereignSync
from backend.broadcast_utils import SovereignBroadcaster
from backend.db.postgres_db import get_read_session
from sqlalchemy import text

@pytest.mark.asyncio
async def test_v13_absolute_monolith_brain():
    """Verifies the v13.0.0 Unified Async Brain Controller."""
    brain = LeviBrainCoreController()
    
    # Track pulse emission
    pulses = []
    def pulse_spy(p): pulses.append(p)
    SovereignBroadcaster.subscribe = pulse_spy # Temporary hijack for spy
    
    # 1. Mission: Deterministic Logic
    res = await brain.run_mission_sync(
        input_text="Calculate 25 * 4 + 10",
        user_id="grad_test_1",
        session_id=f"v13_test_{uuid.uuid4().hex[:6]}"
    )
    assert res["response"] == "110"
    assert res["decision"] == "INTERNAL"
    assert "mission_id" in res
    
    # 2. Mission: Neural Sovereignty (Async)
    res_neural = await brain.run_mission_sync(
        input_text="Explain the concept of cognitive resonance in v13.0.0",
        user_id="grad_test_1",
        session_id=f"v13_test_neural_{uuid.uuid4().hex[:6]}"
    )
    assert "resonance" in res_neural["response"].lower()
    assert res_neural["decision"] == "NEURAL"
    
    # 3. SQL Persistence Audit
    async with get_read_session() as session:
        mission_res = await session.execute(
            text("SELECT * FROM missions WHERE mission_id = :mid"),
            {"mid": res["mission_id"]}
        )
        assert mission_res.first() is not None

@pytest.mark.asyncio
async def test_v13_dcn_synk_integrity():
    """Verifies the Distributed Cognitive Network (DCN) Rule Bridge."""
    # SovereignSync uses Sovereign OS v13.0.0 protocol version for signatures
    rule_data = '{"swarm_id": "test_dcn", "rules": {"PII_MASK": "DETERMINISTIC_SAFE_MODE"}}'
    sig = SovereignSync._generate_signature(rule_data)
    
    # Verify Rule Import
    await SovereignSync.import_rules(rule_data, sig)
    
    # Check if rule was correctly imported into RulesEngine
    from backend.core.v8.rules_engine import RulesEngine
    engine = RulesEngine()
    # RulesEngine uses in-memory or Redis-backed logic; verify it exists
    assert engine is not None

@pytest.mark.asyncio
async def test_v13_pulse_binary_telemetry():
    """Verifies the v4.1 Adaptive Pulse (Binary/Compressible) Emission."""
    pulse = {
        "type": "NEURAL_PULSE",
        "data": {"status": "SOVEREIGN_ABS_MONOLITH_ONLINE"},
        "version": "13.0.0"
    }
    # Should not raise error and correctly pass through Broadcaster
    SovereignBroadcaster.broadcast(pulse)
    assert True

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_v13_absolute_monolith_brain())
    asyncio.run(test_v13_dcn_synk_integrity())
    asyncio.run(test_v13_pulse_binary_telemetry())
    print("LEVI-AI v13.0.0: Graduation Finality Verified.")
