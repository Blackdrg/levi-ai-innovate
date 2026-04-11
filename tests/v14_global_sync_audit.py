# tests/v14_global_sync_audit.py
import pytest
import asyncio
import json
import os
from backend.services.mcm import mcm_service
from backend.utils.global_gossip import global_swarm_bridge

@pytest.mark.asyncio
async def test_global_cognitive_pulse_sync():
    """
    Sovereign v14.2.0: Global Sync Audit.
    Verifies that a cognitive event in Region A (Simulated) is 
    correctly relayed to the Global Pulse Bus.
    """
    # 1. Setup Mock Pulse
    mcm_service.region = "us-east1"
    mcm_service.project_id = "test-project"
    
    # Mock Publisher
    class MockPublisher:
        def __init__(self):
            self.published = []
        def topic_path(self, project, topic): return f"projects/{project}/topics/{topic}"
        def publish(self, path, data): self.published.append(data)
        
    mcm_service.publisher = MockPublisher()
    
    # 2. Emit Regional Event
    payload = {"input": "Hello", "response": "Sovereign"}
    await mcm_service._process_event(
        "interaction", "user_123", "session_abc", 
        payload, source_region="us-east1"
    )
    
    # 3. Verify Global Relay
    assert len(mcm_service.publisher.published) == 1
    relayed_data = json.loads(mcm_service.publisher.published[0].decode())
    assert relayed_data["type"] == "interaction"
    assert relayed_data["source_region"] == "us-east1"
    print("✅ Global Pulse Relay Verified.")

@pytest.mark.asyncio
async def test_global_gossip_standardization():
    """Verifies that the gossip bridge uses the standardized v14.2 topic."""
    assert global_swarm_bridge.TOPIC_ID == "sovereign-cognitive-pulse"
    print("✅ Gossip Topic Standardization Verified.")

if __name__ == "__main__":
    asyncio.run(test_global_cognitive_pulse_sync())
    asyncio.run(test_global_gossip_standardization())
