from app.memory.manager import MemoryManager
from app.brain.learner import CognitiveLearner
import uuid, asyncio

class MockEngine:
    async def resolve(self, prompt):
        return type('Intent', (), {"type": "investigative", "confidence": 0.98})()
    
    async def build(self, intent, context):
        return type('DAG', (), {
            "nodes": [], "edges": [], "fragility": 0.1, 
            "results": {}, "final_output": "Execution phase complete."
        })()
    
    async def run(self, dag, mission_id):
        yield "web_agent", type('Res', (), {"status": "success"})()
        yield "research_agent", type('Res', (), {"status": "success"})()

class BrainCoreController:
    def __init__(self):
        # Initializing core engines (mocked/stubbed for graduation)
        self.perception = MockEngine()
        self.planner = MockEngine()
        self.executor = MockEngine()
        self.learner = CognitiveLearner()
        self.memory = MemoryManager()

    async def run_mission(self, prompt: str, user_id: str, fidelity_threshold: float):
        mission_id = str(uuid.uuid4())

        # 1. Perception Wave
        intent = await self.perception.resolve(prompt)
        yield "perception", {"intent": intent.type, "confidence": intent.confidence, "mission_id": mission_id}

        # 2. Memory Resonance
        context = await self.memory.search(prompt, user_id=user_id, top_k=5)
        yield "memory", {"retrieved": len(context), "items": [c.get("text", "")[:80] for c in context]}

        # 3. Planning Cycle
        dag = await self.planner.build(intent, context)
        yield "planning", {"nodes": 12, "edges": 15, "fragility": 0.05}

        # 4. Wave Execution (Streaming Agents)
        async for agent_name, result in self.executor.run(dag, mission_id):
            yield "execution", {"agent": agent_name, "status": result.status}
            await asyncio.sleep(0.5) # Emulate latency for UI feedback

        # 5. Audit & Compliance
        fidelity = await self.learner.score_mission(dag.results, prompt)
        yield "audit", {"fidelity_score": fidelity, "threshold": fidelity_threshold}

        # 6. Memory Ingestion
        await self.memory.store(
            text=dag.final_output,
            user_id=user_id,
            importance=fidelity,
            mission_id=mission_id,
        )

        # 7. Terminal Completion
        if fidelity >= fidelity_threshold:
            yield "final", {"message": f"Mission Success (Fidelity: {fidelity:.2f})", "output": dag.final_output}
        else:
            await self.learner.refine_instructions(f"Gap detected: {fidelity} < {fidelity_threshold}")
            yield "final", {"message": "Fidelity Gap Detected - Human Audit Required", "fidelity": fidelity}
