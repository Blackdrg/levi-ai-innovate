import asyncio
import logging
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Dict, Any, List

from backend.core.memory_manager import MemoryManager
from backend.kafka_client import LeviKafkaClient

logger = logging.getLogger("memory_service")
app = FastAPI(title="LeviBrain v8 Memory Service")

memory_manager = MemoryManager()

class MemoryQuery(BaseModel):
    user_id: str
    session_id: str
    query: str = ""

@app.on_event("startup")
async def startup():
    logger.info("Memory Service starting...")
    # 1. Listen for memory update events (episodic/semantic)
    asyncio.create_task(LeviKafkaClient.consume_events("memory.updates", process_memory_update))

async def process_memory_update(event: Dict[str, Any]):
    user_id = event.get("user_id")
    session_id = event.get("session_id")
    user_input = event.get("user_input")
    response = event.get("response")
    
    # 2. Asynchronous storage and distillation
    await memory_manager.store_memory(user_id, session_id, user_input, response)

@app.post("/context")
async def get_context(query: MemoryQuery):
    """Retrieve 4-tier context for the brain."""
    context = await memory_manager.get_combined_context(
        user_id=query.user_id, 
        session_id=query.session_id, 
        query=query.query
    )
    return context
