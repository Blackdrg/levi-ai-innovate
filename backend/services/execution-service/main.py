import asyncio
import logging
from fastapi import FastAPI
from shared.schemas import Goal, TaskNode

from backend.core.v8.executor import GraphExecutor
from backend.kafka_client import LeviKafkaClient, emit_brain_event

logger = logging.getLogger("execution_service")
app = FastAPI(title="LeviBrain v8 Execution Service")

executor = GraphExecutor()

@app.on_event("startup")
async def startup():
    logger.info("Execution Service starting...")
    # 1. Start Kafka Consumer Loop
    from backend.utils.runtime_tasks import create_tracked_task
    create_tracked_task(LeviKafkaClient.consume_events("execution.missions", process_mission), name="kafka-execution-consumer")

async def process_mission(mission_payload: Dict[str, Any]):
    request_id = mission_payload.get("request_id")
    logger.info(f"[Execution-Service] New Mission: {request_id}")
    
    # Reconstruct Task Graph from node list
    from backend.core.v8.planner import TaskGraph
    graph = TaskGraph(nodes=[TaskNode(**n) for n in mission_payload.get("graph", [])])
    
    # 2. Parallel Graph Execution
    # Context should be provided in the payload
    perception = {
        "input": mission_payload.get("user_input"),
        "context": mission_payload.get("context", {}),
        "user_id": mission_payload.get("user_id"),
        "session_id": mission_payload.get("session_id")
    }
    
    results = await executor.run(graph, perception)
    
    # 3. Handle Reflection & Synthesis
    from backend.core.v8.critic import ReflectionEngine
    reflection = ReflectionEngine()
    
    from backend.services.orchestrator.engine import synthesize_response
    response = await synthesize_response(results, perception["context"])
    
    # Use goal for reflection pass
    goal = Goal(**mission_payload.get("goal", {}))
    evaluation = await reflection.evaluate(response, goal, perception)
    
    if not evaluation["is_satisfactory"]:
        await emit_brain_event("reflection.retry", {"request_id": request_id, "score": evaluation["score"]})
        response = await reflection.self_correct(response, evaluation, goal, perception)
        
    # 4. Mission Accomplished: Emit Result
    await emit_brain_event("response.final", {
        "request_id": request_id, 
        "response": response,
        "results": [r.dict() for r in results],
        "user_id": perception["user_id"],
        "session_id": perception["session_id"]
    })
