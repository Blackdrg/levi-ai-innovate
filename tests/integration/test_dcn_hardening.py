import pytest
import asyncio
import os
import hmac
import hashlib
import json
import time
from backend.core.dcn_protocol import DCNProtocol, DCNPulse

@pytest.mark.asyncio
async def test_multi_region_dcn_verification():
    """
    Sovereign DCN Hardening: DCN_001.
    Tests SECURE pulse verification and regional identity across the cluster.
    """
    # Force a shared secret for the test
    test_secret = "test_sovereign_secret_32_characters_long_min"
    os.environ["DCN_SECRET"] = test_secret
    
    # 1. Initialize two logical nodes
    node_a = DCNProtocol(node_id="node-US-01", region="us-east-1")
    node_b = DCNProtocol(node_id="node-EU-01", region="eu-central-1")
    
    # 2. Node A creates a signed pulse
    payload = {"message": "Sovereign Link Established", "type": "heartbeat"}
    pulse_a = DCNPulse(
        node_id=node_a.node_id,
        region=node_a.region,
        payload_type="heartbeat",
        payload=payload,
        timestamp=time.time(),
        term=1
    )
    
    msg_json = pulse_a.model_dump_json(exclude={"signature"})
    pulse_a.signature = hmac.new(test_secret.encode(), msg_json.encode(), hashlib.sha256).hexdigest()
    
    # 3. Node B verifies Node A's pulse
    is_valid = await node_b.verify_pulse(pulse_a)
    assert is_valid is True, "Cross-node signature verification failed."
    
    # 4. Peer Discovery Proof
    await node_b.handle_remote_pulse(pulse_a)
    assert node_a.node_id in node_b.peers, "Node A not discovered by Node B."
    
    print(f"✅ Multi-region DCN Pulse Verified: {node_a.node_id} (US) -> {node_b.node_id} (EU)")

@pytest.mark.asyncio
async def test_quorum_calc_diversity():
    """
    Sovereign DCN Hardening: DCN_002.
    Tests Regional Diversity enforcement in Quorum calculations.
    """
    node = DCNProtocol(node_id="main-node", region="us-east-1")
    node.peers = {"node-1", "node-2", "node-3"} # Total 4 nodes (inc self)
    
    # Needs (4//2)+1 = 3 votes
    
    # Case 1: Enough votes but same region
    assert node.verify_quorum(votes=3, regional_diversity=["us-east-1", "us-east-1", "us-east-1"], enforce_diversity=True) == False
    
    # Case 2: Enough votes and diverse regions
    assert node.verify_quorum(votes=3, regional_diversity=["us-east-1", "us-west-2", "eu-central-1"], enforce_diversity=True) == True
    
    print("✅ Regional Quorum Diversity Calculation Verified.")
