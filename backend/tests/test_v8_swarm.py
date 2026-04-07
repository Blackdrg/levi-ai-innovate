import pytest
import asyncio
import json
from backend.core.v8.planner import DAGPlanner
from backend.core.v8.learning import FragilityTracker
from backend.core.v8.agents.consensus import ConsensusAgentV8, ConsensusInput
from backend.memory.cache import MemoryCache

@pytest.mark.asyncio
async def test_swarm_explosion():
    planner = DAGPlanner()
    user_id = "test_user_swarm"
    intent_type = "code"
    
    # 1. Set High Fragility
    MemoryCache.delete(f"fragility:{user_id}:{intent_type}")
    FragilityTracker.record_outcome(user_id, intent_type, success=False)
    FragilityTracker.record_outcome(user_id, intent_type, success=False) # Fragility should be ~0.8
    
    perception = {
        "user_id": user_id,
        "input": "Fix the binary search algorithm",
        "intent": type('Intent', (), {'intent_type': intent_type, 'complexity_level': 5})()
    }
    
    goal = type('Goal', (), {'objective': 'Fix code', 'success_criteria': []})()
    
    graph = await planner.build_task_graph(goal, perception)
    
    # 2. Verify Swarm nodes
    swarm_nodes = [n for n in graph.nodes if n.id.startswith("t_swarm_code")]
    assert len(swarm_nodes) == 5
    
    # 3. Verify Mood distribution (70/30)
    # 5 * 0.7 = 3.5 -> 3 Precise, 2 Creative
    precise_count = len([n for n in swarm_nodes if n.metadata.get("mood") == "precise"])
    creative_count = len([n for n in swarm_nodes if n.metadata.get("mood") == "creative"])
    
    assert precise_count == 3
    assert creative_count == 2
    
    # 4. Verify Consensus dependency
    consensus_node = next(n for n in graph.nodes if n.id == "t_consensus")
    assert all(sn.id in consensus_node.dependencies for sn in swarm_nodes)

@pytest.mark.asyncio
async def test_consensus_logic():
    agent = ConsensusAgentV8()
    
    # Mock outputs
    outputs = {
        "t_swarm_code_0": "The bug is on line 42.",
        "t_swarm_code_1": "The bug is on line 42. It's an index error.",
        "t_swarm_code_2": "Everything looks fine, no bug.",
        "t_swarm_code_3": "Line 42 has a off-by-one error.",
        "t_swarm_code_4": "I agree with line 42 being the issue."
    }
    
    # We mock council_of_models to return a specific consensus analysis
    original_council = agent.generator.council_of_models
    
    async def mock_analysis(messages, temperature=0.2):
        if "Perform a logical intersection" in messages[-1]["content"]:
            return json.dumps({
                "conflicts": ["Agent 2 disagrees with the others"],
                "agreement_score": 0.8
            })
        return "Consensus reached: The bug is on line 42 (Index/Off-by-one error)."

    agent.generator.council_of_models = mock_analysis
    
    input_data = ConsensusInput(
        input="Find the bug",
        agent_outputs=outputs,
        fragility_score=0.8
    )
    
    res = await agent._execute_system(input_data, {})
    
    assert res.success
    assert "Line 42" in res.message
    assert res.data["agreement_score"] == 0.8
    assert res.data["strategy"] == "unified_synthesis" # 0.8 > 0.6
    
    agent.generator.council_of_models = original_council

if __name__ == "__main__":
    asyncio.run(test_swarm_explosion())
    asyncio.run(test_consensus_logic())
    print("Swarm Orchestration Tests Passed Locally.")
