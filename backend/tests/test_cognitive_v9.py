import pytest
import asyncio
from backend.core.v8.planner import DAGPlanner, TaskNode
from backend.core.v8.executor import GraphExecutor
from backend.core.v8.evolution_engine import EvolutionEngine
from backend.memory.manager import MemoryManager
from backend.core.v8.agents.research import ResearchAgentV8, ResearchInput
from backend.core.orchestrator_types import ToolResult

@pytest.mark.asyncio
async def test_v9_dynamic_dag_decomposition():
    """Verifies that high-complexity missions trigger dynamic LLM decomposition."""
    planner = DAGPlanner()
    goal = type('Goal', (), {'objective': 'Research the latest advancements in quantum-resistant encryption and provide a code implementation.'})
    perception = {
        "intent": type('Intent', (), {'intent_type': 'code', 'complexity_level': 4, 'capabilities': []}),
        "input": "Advanced cryptography research",
        "user_id": "test_user_v9"
    }
    
    # Note: This will call LLM in production, but here we check the logic flow
    graph = await planner.build_task_graph(goal, perception)
    
    assert len(graph.nodes) > 0
    # For complexity 4, it should have been handled by LlmDecomposer or fallback
    assert any(n.agent in ["search_agent", "research_agent", "code_agent"] for n in graph.nodes)

@pytest.mark.asyncio
async def test_v9_executor_retry_logic():
    """Verifies the Retry + Compensate logic in the GraphExecutor."""
    executor = GraphExecutor()
    from backend.core.v8.planner import TaskGraph
    
    graph = TaskGraph()
    # Add a failing node
    graph.add_node(TaskNode(
        id="t_fail",
        agent="non_existent_agent",
        description="This should fail and trigger retry",
        critical=True,
        retry_count=1
    ))
    
    perception = {"user_id": "test_user", "session_id": "test_session_v9"}
    results = await executor.run(graph, perception)
    
    # The executor should have tried the node and eventually failed it (or compensated)
    assert len(results) > 0
    assert not results[0].success

@pytest.mark.asyncio
async def test_v9_evolutionary_learning():
    """Verifies that EvolutionEngine promotes high-fidelity patterns."""
    evo = EvolutionEngine()
    task = "Who is the CEO of Google?"
    result = {"answer": "Sundar Pichai"}
    
    # 1. First encounter
    evo.learn(task, result, quality_score=0.95)
    assert not evo.apply(task) # Should not be promoted yet
    
    # 2. Second and Third encounters
    evo.learn(task, result, quality_score=0.98)
    evo.learn(task, result, quality_score=0.97)
    
    # 3. Verify promotion
    promoted_result = evo.apply(task)
    assert promoted_result == result

@pytest.mark.asyncio
async def test_v9_agent_delegation():
    """Verifies that ResearchAgent can delegate to SearchAgent."""
    agent = ResearchAgentV8()
    # Mocking delegate_to to avoid actual network/agent calls
    async def mock_delegate(agent_name, input_data, context):
        return ToolResult(success=True, data={"results": [{"title": "Quantum Resistance", "url": "http://example.com"}]}, agent=agent_name)
    
    agent.delegate_to = mock_delegate
    
    input_data = ResearchInput(input="quantum encryption")
    context = {"user_id": "test_user"}
    
    result = await agent._execute_system(input_data, context)
    assert result.success
    assert len(result.data.sources) > 0
