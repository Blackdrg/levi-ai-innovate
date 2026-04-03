import asyncio
import logging
from backend.core.v8.brain import LeviBrainV8
from backend.core.v8.goal_engine import GoalEngine
from backend.core.v8.learning import LearningLoopV8

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_v8_cognitive_pipeline():
    print("\n--- INITIATING LEVIBRAIN V8 CORE VERIFICATION ---\n")
    brain = LeviBrainV8()
    
    # 1. Perception/Goal Test
    print("Testing Goal Engine [Mission Formulation]...")
    goal_engine = GoalEngine()
    perception = {
        "input": "Build a Python script that scrapes AI news and summarizes them into a technical report.",
        "intent": type('Intent', (), {"intent_type": "code", "complexity_level": 3})()
    }
    goal = await goal_engine.create_goal(perception)
    print(f"Goal Objective: {goal.objective}")
    print(f"Success Criteria Count: {len(goal.success_criteria)}")
    assert len(goal.success_criteria) >= 3, "Goal criteria should be multi-layered."

    # 2. Learning Loop Test [Trait Distillation]
    print("\nTesting Learning Loop [Trait Distillation]...")
    mock_event = {
        "id": "mission_001",
        "input": "Quantum encryption logic",
        "summary": "Successfully architected quantum-safe AES wrapper.",
        "methodology": "Architectural layering with NTRU Prime.",
        "rating": 5,
        "fidelity": 0.95
    }
    await LearningLoopV8.process_feedback(mock_event)
    print("Trait distillation pulse sent to Kafka client.")

    # 3. Importance Decay Test
    print("\nTesting Importance Decay [Memory Pruning]...")
    mock_memories = [
        {"id": "mem_1", "timestamp": "2020-01-01T00:00:00Z", "importance": 1}, # Old, low importance (Should decay)
        {"id": "mem_2", "timestamp": "2026-04-01T00:00:00Z", "importance": 9}  # Recent, high importance (Should survive)
    ]
    survivors = await LearningLoopV8.apply_importance_decay(mock_memories)
    print(f"Memory survivors: {len(survivors)} / 2")
    assert len(survivors) == 1, "Decay heuristic failed to prune old/low-resonance memory."

    print("\n--- V8 CORE VERIFICATION COMPLETE ---")

if __name__ == "__main__":
    asyncio.run(test_v8_cognitive_pipeline())
