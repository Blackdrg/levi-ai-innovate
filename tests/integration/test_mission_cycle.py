import pytest
import asyncio
import uuid
from backend.core.orchestrator import Orchestrator
from backend.db.connection import PostgresSessionManager
from backend.db.models import Mission, UserProfile

@pytest.fixture
async def setup_test_user():
    user_id = f"test-user-{uuid.uuid4().hex[:8]}"
    async with await PostgresSessionManager.get_scoped_session() as session:
        profile = UserProfile(user_id=user_id, role="admin")
        session.add(profile)
        await session.commit()
    return user_id

@pytest.mark.asyncio
async def test_full_mission_cycle(setup_test_user):
    """
    Sovereign Integration: MISSION_CYCLE_001.
    Tests the Orchestrator from perception to memory persistence.
    """
    user_id = setup_test_user
    orchestrator = Orchestrator()
    
    # 1. Pipeline Execution
    result = await orchestrator.handle_mission(
        user_input="Explain the concept of Sovereign AI in 2 sentences.",
        user_id=user_id,
        session_id="test-session",
        mode="creative"
    )
    
    # 2. Assertions
    assert result["status"] == "success"
    assert "response" in result
    assert result["request_id"] is not None
    
    # 3. Persistence Proof
    async with await PostgresSessionManager.get_scoped_session() as session:
        from sqlalchemy import select
        q = select(Mission).where(Mission.mission_id == result["request_id"])
        db_mission = (await session.execute(q)).scalar_one_or_none()
        
        assert db_mission is not None
        assert db_mission.user_id == user_id
        assert db_mission.status == "persisted" # Orchestrator transitions to PERSISTED near the end
        
    print(f"✅ Mission Cycle Verified: {result['request_id']}")

@pytest.mark.asyncio
async def test_dag_resolution_proof(setup_test_user):
    """
    Sovereign Integration: DAG_RESOLUTION_001.
    Tests a complex multi-step plan.
    """
    user_id = setup_test_user
    orchestrator = Orchestrator()
    
    # Force a complex intent
    result = await orchestrator.handle_mission(
        user_input="Research the history of decentralized compute and summarize the top 3 projects.",
        user_id=user_id,
        session_id="test-session"
    )
    
    assert result["status"] == "success"
    # Verify reasoning structure exists
    assert "reasoning" in result
    assert "strategy" in result["reasoning"]
    
    print(f"✅ DAG Execution Proof Verified: {result['request_id']}")
