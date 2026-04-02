import os
import logging
import httpx
from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from backend.kafka_client import LeviKafkaClient
from shared.schemas import IntentResult

logger = logging.getLogger("gateway_service")
app = FastAPI(title="LeviBrain v8 Gateway Service")

# Service URLs from environment
BRAIN_SERVICE_URL = os.getenv("BRAIN_SERVICE_URL", "http://brain-service:8000")
MEMORY_SERVICE_URL = os.getenv("MEMORY_SERVICE_URL", "http://memory-service:8000")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/api/v1/brain/mission")
async def start_mission(request: Request):
    """Entry point for LeviBrain v8 Cognitive Missions."""
    body = await request.json()
    user_input = body.get("input")
    user_id = body.get("user_id", "guest")
    session_id = body.get("session_id", "default")

    async with httpx.AsyncClient() as client:
        # 1. Perception: Get intent and context in parallel (Internal REST)
        # For simplicity, we trigger intent detection here or in brain-service
        # Let's assume brain-service handles full orchestration as implemented
        
        # 2. Get Memory Context
        memory_resp = await client.post(f"{MEMORY_SERVICE_URL}/context", json={
            "user_id": user_id,
            "session_id": session_id,
            "query": user_input
        })
        context = memory_resp.json()

        # 3. Trigger Brain Service
        # We Mock intent for this flow example, or call a dedicated intent service
        from backend.core.v8.brain import detect_intent # Hybrid local/api
        intent = await detect_intent(user_input)

        brain_resp = await client.post(f"{BRAIN_SERVICE_URL}/orchestrate", json={
            "user_input": user_input,
            "user_id": user_id,
            "session_id": session_id,
            "intent": intent,
            "context": context
        })
        
        return brain_resp.json()

@app.get("/api/v1/brain/stream/{request_id}")
async def stream_thoughts(request_id: str):
    """SSE endpoint for Real Intelligence Thought Streaming."""
    
    async def event_generator():
        # Listen to Kafka for events related to this request_id
        # In a real setup, we'd use a Redis pub/sub or a specific Kafka consumer
        # For this walkthrough, we'll demonstrate the concept
        consumer = await LeviKafkaClient.get_consumer(f"brain.*")
        async for msg in consumer:
            data = json.loads(msg.value)
            if data.get("request_id") == request_id:
                yield f"data: {json.dumps(data)}\n\n"

    # Note: Simplified for the blueprint. Real implementation would use 
    # a more robust per-request event routing logic.
    return StreamingResponse(event_generator(), media_type="text/event-stream")

@app.get("/health")
async def health():
    return {"status": "gateway_operational"}
