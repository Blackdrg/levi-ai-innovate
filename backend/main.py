# backend/main.py
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware import CORSMiddleware
from contextlib import asynccontextmanager
import logging
import json

from backend.core.orchestrator import Orchestrator
from backend.core.memory_manager import MemoryManager
from backend.auth.middleware import SovereignShieldMiddleware
from backend.api.middleware.ssrf import SSRFMiddleware
from backend.api.middleware.rate_limiter import RateLimitMiddleware
from backend.auth import get_current_user

# Initialize logger
logger = logging.getLogger("levi")

# Global state
orchestrator: Orchestrator = None
memory_manager: MemoryManager = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    global orchestrator, memory_manager
    
    logger.info("🚀 LEVI-AI Sovereign OS v14.2.0 starting...")
    
    # Initialize core services
    orchestrator = Orchestrator()
    memory_manager = MemoryManager()
    
    await orchestrator.initialize()
    await memory_manager.initialize()
    
    # Start DCN gossip hub
    await orchestrator.dcn_manager.start_gossip_hub()
    
    logger.info("✅ LEVI-AI online and ready for missions")
    
    yield
    
    # Shutdown
    logger.info("🛑 LEVI-AI shutting down...")
    await orchestrator.dcn_manager.stop_gossip_hub()
    await memory_manager.shutdown()
    logger.info("✅ Shutdown complete")

# Create FastAPI app
app = FastAPI(
    title="LEVI-AI Sovereign OS",
    version="14.2.0",
    lifespan=lifespan
)

# Middleware stack (in order)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(SSRFMiddleware)
app.add_middleware(SovereignShieldMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://yourdomain.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
@app.get("/healthz")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": "14.2.0",
        "graduation_score": await orchestrator.get_graduation_score()
    }

@app.post("/api/v1/orchestrator/mission")
async def create_mission(request: dict, current_user = Depends(get_current_user)):
    """Create new cognitive mission"""
    mission = await orchestrator.create_mission(
        user_id=current_user.id,
        objective=request.get("message"),
        mode=request.get("mode", "AUTONOMOUS")
    )
    return mission

@app.get("/api/v1/orchestrator/mission/{mission_id}")
async def get_mission(mission_id: str, current_user = Depends(get_current_user)):
    """Get mission status"""
    mission = await orchestrator.get_mission(mission_id, current_user.id)
    if not mission:
        raise HTTPException(status_code=404, detail="Mission not found")
    return mission

@app.delete("/api/v1/orchestrator/mission/{mission_id}")
async def cancel_mission(mission_id: str, current_user = Depends(get_current_user)):
    """Cancel in-flight mission"""
    await orchestrator.cancel_mission(mission_id, current_user.id)
    return {"status": "cancelled"}

@app.get("/api/v1/telemetry/stream/{mission_id}")
async def stream_mission(mission_id: str, current_user = Depends(get_current_user)):
    """SSE stream for mission telemetry"""
    from fastapi.responses import StreamingResponse
    
    async def event_generator():
        # Stream events from Redis
        async for event in orchestrator.stream_mission_events(mission_id):
            yield f"data: {json.dumps(event)}\n\n"
    
    return StreamingResponse(event_generator(), media_type="text/event-stream")

@app.get("/api/v1/brain/pulse")
async def system_pulse(current_user = Depends(get_current_user)):
    """System health and routing status"""
    return {
        "system_graduation_score": 1.0,
        "vram_pressure": await orchestrator.check_vram_pressure(),
        "active_missions": await orchestrator.count_active_missions(),
        "dcn_health": await orchestrator.get_dcn_health()
    }

@app.get("/metrics")
async def prometheus_metrics():
    """Prometheus metrics endpoint"""
    from prometheus_client import generate_latest
    return generate_latest()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, workers=4)
