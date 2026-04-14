import asyncio
import pytest
import time
from backend.core.dcn.gossip import GossipProtocol, GossipPulse

async def simulate_pulse_delivery(node_a, node_b, node_c):
    """Simulates the mesh network pulse delivery."""
    while True:
        # In a real test, this would be hooked via a message bus
        # Here we manually trigger receive_pulse for demonstration
        await asyncio.sleep(1)

@pytest.mark.asyncio
async def test_gossip_convergence():
    node_a = GossipProtocol("node-a", {"node-b", "node-c"}, interval=1)
    node_b = GossipProtocol("node-b", {"node-a", "node-c"}, interval=1)
    node_c = GossipProtocol("node-c", {"node-a", "node-b"}, interval=1)
    
    # Node A gets a fact
    node_a.local_state['fact_1'] = {'value': 'test', 'timestamp': time.time()}
    
    # Manually simulate pulse reception for the test
    # Pulse from A to B and C
    pulse_a = GossipPulse(
        node_id="node-a",
        term=1,
        facts=node_a.local_state,
        timestamp=time.time(),
        signature=node_a._sign_pulse(node_a.local_state)
    )
    
    await node_b.receive_pulse(pulse_a)
    await node_c.receive_pulse(pulse_a)
    
    # All nodes should have fact_1
    assert 'fact_1' in node_a.local_state
    assert 'fact_1' in node_b.local_state
    assert 'fact_1' in node_c.local_state
    assert node_b.local_state['fact_1']['value'] == 'test'
