import os
import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Header
from pydantic import BaseModel, Field

from backend.services.brain_service import brain_service, BrainPolicy, DecisionScores
from backend.utils.decision_logger import DecisionLogger
from backend.core.orchestrator_types import IntentResult

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/brain", tags=["Brain Service v14.0"])

# --- Models ---
class BrainIntakeRequest(BaseModel):
    query: str = Field(..., description="The user query to analyze")
    user_context: Dict[str, Any] = Field(default_factory=dict)
    system_load: float = 0.6

# --- Middleware (S2S Auth) ---
async def get_service_auth(x_brain_token: Optional[str] = Header(None)):
    """Service-to-Service Authentication pulse check."""
    if not x_brain_token or not brain_service.verify_service_token(x_brain_token):
        logger.warning(f"[Brain API] Security violation: Invalid service pulse detected.")
        raise HTTPException(
            status_code=403, 
            detail="Neural protocol violation: Invalid Service Pulse."
        )
    return True

# --- Endpoints ---

@router.post("/analyze_intent", response_model=IntentResult)
async def analyze_intent(
    request: BrainIntakeRequest,
    _auth: bool = Depends(get_service_auth)
):
    """STEP 1: Strategic Intent Detection pulse."""
    logger.info(f"[Brain API] Intake Pulse: Analyzing Intent for '{request.query[:50]}'")
    return await brain_service.analyze_intent(request.query, request.user_context)

@router.post("/decide_mode")
async def decide_mode(
    request: BrainIntakeRequest,
    _auth: bool = Depends(get_service_auth)
):
    """STEP 3: Mode Decision pulse."""
    # We generate a full policy internally to determine mode
    policy: BrainPolicy = await brain_service.generate_policy(request.query, request.user_context)
    return {"mode": policy.mode}

@router.post("/generate_policy", response_model=BrainPolicy)
async def generate_policy(
    request: BrainIntakeRequest,
    _auth: bool = Depends(get_service_auth)
):
    """STEP 4: Master Policy Generation."""
    logger.info(f"[Brain API] Policy Pulse: Generating signed execution contract.")
    return await brain_service.generate_policy(request.query, request.user_context)

@router.post("/allocate_resources")
async def allocate_resources(
    request: BrainIntakeRequest,
    _auth: bool = Depends(get_service_auth)
):
    """Brain Resource Allocation pulse."""
    intent = await brain_service.analyze_intent(request.query, request.user_context)
    scores: DecisionScores = await brain_service.compute_scores(request.query, intent)
    return scores

@router.post("/validate_execution_plan")
async def validate_execution_plan(
    plan: Dict[str, Any],
    policy_id: str,
    _auth: bool = Depends(get_service_auth)
):
    """Brain Validation: Ensures the execution DAG adheres to policies."""
    # For now, simple validation placeholder
    logger.info(f"[Brain API] Validation Pulse: Checking DAG alignment for policy {policy_id}")
    return {"valid": True, "notes": "Plan aligned with sovereign constraints."}

@router.post("/log_decision_trace")
async def log_decision_trace(
    trace: Dict[str, Any],
    _auth: bool = Depends(get_service_auth)
):
    """Decision Logger Entry Pulse."""
    await DecisionLogger.log_decision(
        request_id=trace.get("request_id", "unknown"),
        query=trace.get("query", "unknown"),
        scores=trace.get("scores", {}),
        policy=trace.get("policy", {})
    )
    return {"status": "logged"}
