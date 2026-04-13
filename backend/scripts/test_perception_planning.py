
import asyncio
import sys
import os
from datetime import datetime

# Add the project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from backend.core.perception import PerceptionEngine
from backend.core.planner import DAGPlanner
from backend.memory.manager import MemoryManager
from backend.core.orchestrator_types import BrainMode

async def main():
    print("🚀 Initializing LEVI Perception & Planning Engine Test...")
    
    # Mock Memory Manager
    class MockMemory:
        async def get_combined_context(self, user_id, session_id, input_text):
            return {"long_term": {"graph_resonance": []}, "mood": "neutral"}
    
    memory = MockMemory()
    perception_engine = PerceptionEngine(memory=memory)
    planner = DAGPlanner()

    user_query = "Search for the latest research on room-temperature superconductors and then summarize the key findings in a table."
    user_id = "test_user"
    session_id = "test_session"

    print(f"\n--- 1. Perception Layer (Input: '{user_query}') ---")
    perception = await perception_engine.perceive(user_query, user_id, session_id)
    print(f"Intent detected: {perception['intent'].intent_type} (Confidence: {perception['intent'].confidence_score:.2f})")

    print("\n--- 2. Planning Layer (Decision) ---")
    decision = await planner.generate_decision(user_query, perception)
    print(f"Mode selected: {decision.mode}")
    
    goal = await planner.create_goal(perception, decision)
    print(f"Goal Objective: {goal.objective}")

    print("\n--- 3. DAG Generation ---")
    task_graph = await planner.build_task_graph(goal, perception, decision)
    print(f"Generated {len(task_graph.nodes)} tasks.")
    
    for node in task_graph.nodes:
        print(f"  - [{node.id}] {node.agent}: {node.description} (Deps: {node.dependencies})")

    print("\n--- 4. Wave Partitioning ---")
    waves = task_graph.get_execution_waves()
    for i, wave in enumerate(waves):
        print(f"  Wave {i+1}: {[node.id for node in wave]}")

    print("\n--- 5. Graph Visualization (Mermaid) ---")
    mermaid = task_graph.generate_mermaid()
    print(mermaid)

if __name__ == "__main__":
    asyncio.run(main())
