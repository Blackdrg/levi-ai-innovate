import logging
import asyncio
import uuid
from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
from typing import Dict, Any, List

from shared.schemas import IntentResult, Goal, TaskNode
from backend.core.v8.goal_engine import GoalEngine
from backend.core.v8.planner import DAGPlanner
from backend.kafka_client import LeviKafkaClient, emit_brain_event

logger = logging.getLogger("brain_service")
app = FastAPI(title="LeviBrain v8 Brain Service")

goal_engine = GoalEngine()
planner = DAGPlanner()

class PerceptionInput(BaseModel):
    user_input: str
    user_id: str
    session_id: str
    intent: IntentResult
    context: Dict[str, Any]

@app.post("/orchestrate")
async def orchestrate(perception: PerceptionInput, background_tasks: BackgroundTasks):
    request_id = f"v8_{uuid.uuid4().hex[:8]}"
    logger.info(f"[Brain-Service] New Mission: {request_id}")

    # 1. Goal Engine
    goal = await goal_engine.create_goal({
        "input": perception.user_input,
        "intent": perception.intent,
        "context": perception.context
    })
    await emit_brain_event("goal", {"request_id": request_id, "objective": goal.objective})

    # 2. Planning Engine (DAG)
    graph = await planner.build_task_graph(goal, {
        "input": perception.user_input,
        "intent": perception.intent,
        "context": perception.context
    })
    graph_dict = graph.dict()
    await emit_brain_event("planning", {"request_id": request_id, "graph": graph_dict})

    # 3. Trigger Execution Service (via Kafka)
    mission_payload = {
        "request_id": request_id,
        "user_input": perception.user_input,
        "user_id": perception.user_id,
        "session_id": perception.session_id,
        "goal": goal.dict(),
        "graph": graph_dict,
        "context": perception.context
    }
    background_tasks.add_task(LeviKafkaClient.send_event, "execution.missions", mission_payload)

    return {"status": "orchestration_started", "request_id": request_id}

@app.on_event("startup")
async def startup():
    logger.info("Brain Service starting...")
