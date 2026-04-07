import asyncio
import logging
from backend.core.v8.agents.consensus import ConsensusAgentV8, ConsensusInput
from backend.core.v8.planner import DAGPlanner

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_v8_consensus_wave():
    print("\n--- INITIATING LEVIBRAIN V8.5 SWARM CONSENSUS VERIFICATION ---\n")
    
    # 1. Consensus Agent Test
    print("Testing Consensus Agent [Conflict Resolution]...")
    agent = ConsensusAgentV8()
    test_input = ConsensusInput(
        input="Is Python 3.12 faster than 3.11?",
        agent_outputs={
            "t_research": "Python 3.12 is significantly faster due to BOLT and specialized adaptive interpreters.",
            "t_analyst": "In most benchmarks, 3.12 shows a 5-10% improvement, but some niche cases are slower."
        }
    )
    result = await agent._execute_system(test_input, {})
    print(f"Reconciled Message: {result.message[:100]}...")
    assert result.success, "Consensus synthesis failed."

    # 2. Planner Debate Injection Test
    print("\nTesting Planner [Debate Wave Injection]...")
    planner = DAGPlanner()
    mock_goal = type('Goal', (), {"objective": "Performance audit", "success_criteria": []})()
    mock_perception = {
        "input": "Compare AI performance across v8 and v7 architectures.",
        "intent": type('Intent', (), {"intent_type": "search", "complexity_level": 4})()
    }
    
    graph = await planner.build_task_graph(mock_goal, mock_perception)
    node_ids = [n.id for n in graph.nodes]
    print(f"Generated Nodes: {node_ids}")
    assert "t_consensus" in node_ids, "Planner failed to inject the t_consensus node for a high-complexity mission."

    print("\n--- V8.5 SWARM CONSENSUS VERIFICATION COMPLETE ---")

if __name__ == "__main__":
    asyncio.run(test_v8_consensus_wave())
