# backend/api/v1/router.py
from fastapi import APIRouter

from backend.api.auth import router as auth_router
from backend.api.orchestrator import router as orchestrator_router
from backend.api.v1.voice import router as voice_router
from backend.api.memory import router as memory_router
from backend.api.compliance import router as compliance_router
from backend.api.goals import router as goals_router
from backend.api.monitor_routes import router as monitor_router
from backend.api.studio import router as studio_router
from backend.api.marketplace import router as marketplace_router
from backend.api.telemetry import router as telemetry_router

router = APIRouter()

router.include_router(auth_router, prefix="/auth")
router.include_router(orchestrator_router, prefix="/orchestrator")
router.include_router(voice_router, prefix="/voice")
router.include_router(memory_router, prefix="/memory")
router.include_router(compliance_router, prefix="/compliance")
router.include_router(goals_router, prefix="/goals")
router.include_router(monitor_router, prefix="/monitor")
router.include_router(studio_router, prefix="/studio")
router.include_router(marketplace_router, prefix="/marketplace")
router.include_router(telemetry_router, prefix="/telemetry")
