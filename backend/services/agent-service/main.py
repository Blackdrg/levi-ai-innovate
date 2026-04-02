import asyncio
import logging
from fastapi import FastAPI
from shared.schemas import ToolResult

from backend.core.v8.agents.research import ResearchAgentV8
from backend.core.v8.agents.code import CodeAgentV8
from backend.core.v8.agents.document import DocumentAgentV8
from backend.core.v8.agents.critic import CriticAgentV8

from backend.kafka_client import LeviKafkaClient

logger = logging.getLogger("agent_service")
app = FastAPI(title="LeviBrain v8 Agent Service")

# Standard Agent Registry for the Service
AGENTS = {
    "research_agent": ResearchAgentV8(),
    "code_agent": CodeAgentV8(),
    "document_agent": DocumentAgentV8(),
    "critic_agent": CriticAgentV8()
}

@app.on_event("startup")
async def startup():
    logger.info("Agent Service starting...")
    # 1. Listen for individual agent task calls (if triggered via Kafka)
    # Most agent calls are currently handled via direct ToolRegistry logic 
    # to maintain low-latency for the execution wave.
    pass

@app.post("/call/{agent_name}")
async def call_agent(agent_name: str, payload: Dict[str, Any]):
    agent = AGENTS.get(agent_name)
    if not agent:
        return {"success": False, "error": f"Agent {agent_name} not found."}
    
    # 2. Schema Transformation
    # Handled within the V8 agent's run() method
    input_cls = agent.__annotations__.get("input_data")
    result = await agent.run(input_cls(**payload), context=payload.get("context", {}))
    
    return result.dict()
