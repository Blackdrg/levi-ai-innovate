# backend/api/v1/router.py
from fastapi import APIRouter

from backend.api.auth import router as auth_router
from backend.api.v1.orchestrator import router as orchestrator_chat_router
from backend.api.v1.orchestrator_routes import router as orchestrator_mission_router
from backend.api.v1.compliance import router as compliance_router
from backend.api.v1.analytics import router as analytics_router
from backend.api.memory import router as memory_router
from backend.api.goals import router as goals_router
from backend.api.monitor_routes import router as monitor_router
from backend.api.studio import router as studio_router
from backend.api.marketplace import router as marketplace_router
from backend.api.v1.voice import router as voice_router
from backend.api.telemetry import router as telemetry_router
from backend.api.v1.evolution import router as evolution_router
from backend.api.v1.perception import router as perception_router


router = APIRouter()

router.include_router(auth_router, prefix="/auth")
router.include_router(orchestrator_chat_router, prefix="/orchestrator")
router.include_router(orchestrator_mission_router)
router.include_router(voice_router, prefix="/voice")
router.include_router(memory_router, prefix="/memory")
router.include_router(compliance_router, prefix="/compliance")
router.include_router(analytics_router, prefix="/analytics")
router.include_router(goals_router, prefix="/goals")
router.include_router(monitor_router, prefix="/monitor")
router.include_router(studio_router, prefix="/studio")
router.include_router(marketplace_router, prefix="/marketplace")
router.include_router(telemetry_router, prefix="/telemetry")
# router.include_router(evolution_router, prefix="/evolution") # Disabled in Phase 0
router.include_router(perception_router, prefix="/perception")

