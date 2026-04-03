import asyncio
import sys
import os

# Add backend to path
sys.path.append(os.path.abspath("."))

from backend.core.task_graph import TaskNode, TaskGraph

async def verify_dag():
    # Setup a simple DAG
    # t1 -> t2
    # t3
    
    graph = TaskGraph()
    graph.add_node(TaskNode(id="t1", agent="agent1", description="task 1"))
    graph.add_node(TaskNode(id="t2", agent="agent2", description="task 2", dependencies=["t1"]))
    graph.add_node(TaskNode(id="t3", agent="agent3", description="task 3"))
    
    print(f"Initial Ready Tasks: {[n.id for n in graph.get_ready_tasks()]}")
    # Should be t1, t3
    
    graph.mark_complete("t1", "result1")
    print(f"Ready Tasks after t1 complete: {[n.id for n in graph.get_ready_tasks()]}")
    # Should be t2, t3
    
    graph.mark_complete("t3", "result3")
    print(f"Ready Tasks after t3 complete: {[n.id for n in graph.get_ready_tasks()]}")
    # Should be t2
    
    graph.mark_complete("t2", "result2")
    print(f"Is Complete: {graph.is_complete()}")
    # Should be True

if __name__ == "__main__":
    asyncio.run(verify_dag())
