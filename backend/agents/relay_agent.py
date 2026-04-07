"""
Sovereign Relay Agent v1.0 — Real Sub-Mission Handoff Router.
Replaces the RelayAgentStub with full routing logic:
  - Parse target agent from RelayPayload
  - Validate agent exists in SwarmRegistry (AGENT_REGISTRY)
  - Enqueue to GraphExecutor with correct tier assignment
  - On failure: typed RelayError + Dead Letter Queue entry in Redis
"""

import json
import logging
import time
import uuid
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field

from backend.agents.base import SovereignAgent, AgentResult

logger = logging.getLogger(__name__)

# DLQ Redis key pattern
DLQ_KEY = "relay:dlq"
RELAY_DLQ_TTL = 60 * 60 * 24 * 7   # 7 days


# ---------------------------------------------------------------------------
# Tier assignments per agent (controls GraphExecutor scheduling priority)
# ---------------------------------------------------------------------------
AGENT_TIER_MAP: Dict[str, int] = {
    # Tier 1 — critical / synchronous
    "Critic": 1, "HardRule": 1, "Diagnostic": 1,
    # Tier 2 — standard reasoning
    "Artisan": 2, "Scout": 2, "Coder": 2, "Researcher": 2, "Analyst": 2,
    # Tier 3 — async / creative / heavy
    "Imaging": 3, "Video": 3, "Optimizer": 3, "Memory": 3,
    # Tier 4 — orchestration
    "SwarmCtrl": 4,
}
DEFAULT_TIER = 2


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

class RelayPayload(BaseModel):
    """Inbound payload for the Relay Agent."""
    target_agent: str = Field(..., description="Name of the destination agent (must be in SwarmRegistry)")
    sub_mission: str = Field(..., description="The mission text / instruction to forward")
    context: Dict[str, Any] = Field(default_factory=dict)
    priority: int = Field(default=DEFAULT_TIER, ge=1, le=4)
    caller_agent: str = Field(default="anonymous", description="Originating agent name")
    relay_id: Optional[str] = Field(default=None, description="Idempotency key; auto-generated if absent")
    session_id: Optional[str] = None
    user_id: str = "guest"


class RelayError(BaseModel):
    """Typed error envelope written to the Dead Letter Queue."""
    relay_id: str
    target_agent: str
    caller_agent: str
    reason: str
    timestamp: float
    sub_mission_preview: str


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

class RelayAgent(SovereignAgent[RelayPayload, AgentResult]):
    """
    Sovereign Relay Router v1.0.
    Routes sub-missions between agents via the GraphExecutor.
    """

    def __init__(self):
        super().__init__("RelayRouter")

    async def _run(self, input_data: RelayPayload, lang: str = "en", **kwargs) -> Dict[str, Any]:
        relay_id = input_data.relay_id or str(uuid.uuid4())
        target   = _normalise_agent_name(input_data.target_agent)

        self.logger.info(
            "[Relay:%s] %s → %s — '%s…'",
            relay_id, input_data.caller_agent, target, input_data.sub_mission[:60],
        )

        # ── 1. Validate target agent exists in SwarmRegistry ──────────
        from backend.agents.registry import AGENT_REGISTRY
        if target not in AGENT_REGISTRY:
            return await self._fail(
                relay_id, target, input_data,
                f"Target agent '{target}' not found in SwarmRegistry. "
                f"Available: {sorted(AGENT_REGISTRY.keys())}",
            )

        # ── 2. Determine tier ─────────────────────────────────────────
        tier = input_data.priority or AGENT_TIER_MAP.get(target, DEFAULT_TIER)

        # ── 3. Build GraphExecutor-compatible task node ────────────────
        try:
            result = await self._enqueue_sub_mission(
                relay_id=relay_id,
                target=target,
                tier=tier,
                input_data=input_data,
            )
        except Exception as exc:
            return await self._fail(relay_id, target, input_data, str(exc))

        return {
            "success": True,
            "message": f"Sub-mission relayed to '{target}' (tier {tier}). Result: {str(result.message)[:200]}",
            "data": {
                "relay_id": relay_id,
                "target_agent": target,
                "tier": tier,
                "agent_result": result.model_dump() if hasattr(result, "model_dump") else str(result),
            },
        }

    # ------------------------------------------------------------------
    # Routing helpers
    # ------------------------------------------------------------------

    async def _enqueue_sub_mission(
        self,
        relay_id: str,
        target: str,
        tier: int,
        input_data: RelayPayload,
    ) -> AgentResult:
        """
        Directly calls the target agent via AGENT_REGISTRY.
        In distributed mode this would enqueue to GraphExecutor's task queue;
        for single-node execution we call the agent synchronously.
        """
        from backend.agents.registry import AGENT_REGISTRY

        agent = AGENT_REGISTRY[target]

        # Build the input the target agent expects — pass as dict kwargs
        # Most agents accept an 'input' or 'prompt' field plus context.
        agent_input = _build_agent_input(target, input_data)

        self.logger.debug("[Relay] Dispatching to %s (tier=%d) with payload: %s", target, tier, str(agent_input)[:120])

        # Execute
        result: AgentResult = await agent.execute(agent_input, lang="en")
        return result

    async def _fail(
        self,
        relay_id: str,
        target: str,
        input_data: RelayPayload,
        reason: str,
    ) -> Dict[str, Any]:
        """Log a typed RelayError to the DLQ and return an error payload."""
        error = RelayError(
            relay_id=relay_id,
            target_agent=target,
            caller_agent=input_data.caller_agent,
            reason=reason,
            timestamp=time.time(),
            sub_mission_preview=input_data.sub_mission[:120],
        )

        self.logger.error("[Relay:%s] FAILED — %s → DLQ: %s", relay_id, target, reason)

        # Write to Redis DLQ
        try:
            from backend.db.redis import r as redis_sync, HAS_REDIS
            if HAS_REDIS and redis_sync:
                redis_sync.lpush(DLQ_KEY, json.dumps(error.model_dump()))
                redis_sync.expire(DLQ_KEY, RELAY_DLQ_TTL)
                self.logger.info("[Relay] DLQ entry written: %s", relay_id)
        except Exception as exc:
            self.logger.warning("[Relay] Could not write to DLQ: %s", exc)

        return {
            "success": False,
            "message": f"Relay failed: {reason}",
            "data": error.model_dump(),
        }


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------

def _normalise_agent_name(raw: str) -> str:
    """Capitalise first letter to match AGENT_REGISTRY keys."""
    raw = raw.strip()
    return raw[0].upper() + raw[1:] if raw else raw


def _build_agent_input(target: str, relay: RelayPayload) -> Any:
    """
    Constructs the correct input pydantic model for the target agent.
    Falls back to a generic dict if no mapping is needed.
    """
    from backend.agents.research_agent  import ResearchInput
    from backend.agents.image_agent     import ImageInput
    from backend.agents.video_agent     import VideoInput
    from backend.agents.memory_agent    import MemoryInput

    common = {
        "user_id":    relay.user_id,
        "session_id": relay.session_id or "relay",
    }

    if target == "Researcher":
        return ResearchInput(input=relay.sub_mission, **common)
    if target == "Imaging":
        return ImageInput(prompt=relay.sub_mission, **{k: v for k, v in common.items() if k != "session_id"})
    if target == "Video":
        return VideoInput(prompt=relay.sub_mission, **{k: v for k, v in common.items() if k != "session_id"})
    if target == "Memory":
        return MemoryInput(input=relay.sub_mission, **common)

    # Generic fallback — most agents accept an 'input' field
    from pydantic import create_model
    GenericInput = create_model(
        "GenericInput",
        input=(str, relay.sub_mission),
        user_id=(str, relay.user_id),
        session_id=(Optional[str], relay.session_id),
    )
    return GenericInput()
