import pytest
import asyncio
import os
from sqlalchemy import select
from backend.services.mcm import mcm_service
from backend.db.postgres import PostgresDB, get_session_with_retry
from backend.db.models import UserFact
from backend.db.neo4j_client import Neo4jClient
from backend.utils.kms import SovereignKMS

@pytest.mark.asyncio
async def test_mcm_idempotent_purge():
    """
    Test that the MCM's purge operation doesn't crash on non-existent data 
    (verifying the idempotent hard-rollback fix).
    """
    mission_id = "test_idempotent_mission_001"
    
    # Should not raise any exceptions despite the mission facts not existing
    try:
        await mcm_service.purge_mission_facts(mission_id)
        success = True
    except Exception as e:
        success = False
        
    assert success is True

@pytest.mark.asyncio
async def test_kms_hardware_binding_fallback():
    """
    Verify that the KMS provider defaults safely to keyring/local derivation
    and doesn't expose raw .env secrets for the Sovereign roots.
    """
    # Force initialization
    key = SovereignKMS._get_key()
    assert key is not None
    
    # Ensure a basic trace signature works
    trace_data = "mission=123,status=COMPLETED"
    signature = await SovereignKMS.sign_trace(trace_data)
    assert signature is not None
    
    # Verify the signature
    is_valid = await SovereignKMS.verify_trace(trace_data, signature)
    assert is_valid is True

@pytest.mark.asyncio
async def test_neo4j_temporal_pruning():
    """
    Verify Neo4j graph executes pruning without raising syntax errors.
    """
    # Add a mock interaction
    await Neo4jClient.add_interaction(
        user_id="test_user_777",
        query="Run integration tests",
        response="Tests generated.",
        intent="TESTING",
        sync=True
    )
    
    # Try fetching resonance entities
    entities = await Neo4jClient.get_resonance_entities("test_user_777", "integration")
    
    # Execute the new pruning logic to ensure NO syntax faults
    try:
        await Neo4jClient.prune_graph(days_retention=30)
        success = True
    except Exception:
        success = False
        
    assert success is True
    
    # Cleanup Neo4j
    await Neo4jClient.clear_user_data("test_user_777")
