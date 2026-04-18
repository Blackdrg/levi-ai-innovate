"""
LEVI-AI Sovereign OS v22.0.0
SOVEREIGN KERNEL MAINFRAME — Orchestrator

ARCHITECTURAL REALITY (honest):
  The Orchestrator is the Python-layer mission dispatcher. It:
    1. Accepts user requests from the FastAPI API layer.
    2. Applies admission control (VRAM backpressure, safety gate).
    3. Delegates cognitive work to LeviBrain (singleton).
    4. Runs post-execution crystallization (learning, evolution, audit, mesh).
    5. Manages background workers: sentinel loop, DCN pulse, self-healing.

  The Rust kernel (kernel_wrapper) handles:
    - GPU VRAM governance
    - Process spawning / isolation
    - BFT signature verification
    - Filesystem snapshot

  The Brain (LeviBrain singleton) handles:
    - All cognitive reasoning: perception → plan → execute → reflect
"""

import logging
import uuid
import os
import time
import hashlib
import json
import asyncio
import psutil
import shutil
import platform
import socket
import datetime
import hmac
from typing import Any, Dict, Optional, List, Union, AsyncGenerator, Tuple, Set, Callable
from datetime import timezone

# ── Core cognitive engines ────────────────────────────────────────────────────
from .perception import PerceptionEngine
from .planner import DAGPlanner
from .executor import GraphExecutor
from .reasoning_core import ReasoningCore
from .world_model import WorldModel
from .failure_engine import FailurePolicyEngine
from .reflection import ReflectionEngine
from .evolution_engine import EvolutionaryIntelligenceEngine
from .policy_gradient import policy_gradient
from .alignment import alignment_engine
from .workflow_engine import WorkflowEngine
from .context_manager import ContextManager
from .learning_loop import LearningLoop
from .identity import identity_system

# ── Persistence & mesh layers ─────────────────────────────────────────────────
from backend.services.audit_ledger import audit_ledger
from backend.services.brain_service import brain_service
from backend.services.memory_manager import MemoryManager
from backend.services.cache_manager import CacheManager
from backend.services.billing import CognitiveBilling
from backend.utils.event_bus import sovereign_event_bus
from backend.core.task_manager import task_manager
from backend.db.redis import get_redis_client, state_bridge, HAS_REDIS
from backend.evaluation.tracing import CognitiveTracer
from backend.utils.logging_context import log_request_id, log_user_id, log_session_id
from backend.utils.metrics import MetricsHub, MISSION_COMPLETED, MISSION_ABORTED, GRADUATION_SCORE
from backend.utils.tracing import traced_span
from backend.utils.latency_tracer import LatencyTracer
from backend.kernel.kernel_wrapper import kernel
from backend.utils.kms import SovereignKMS
from backend.services.graduation import graduation_service

# ── DCN / swarm ───────────────────────────────────────────────────────────────
from .dcn.registry import dcn_registry
from .execution_state import CentralExecutionState, MissionState
from .dcn.raft_consensus import get_dcn_mesh

# ─────────────────────────────────────────────────────────────────────────────
OS_VERSION       = "v22.0.0-SOVEREIGN"
KERNEL_ID        = socket.gethostname()
NODE_SECRET      = os.getenv("DCN_SECRET", "sovereign_fallback")
VRAM_ADMISSION   = 0.94    # fraction — missions blocked above this
VRAM_CRITICAL    = 0.98
MISSION_TTL_SEC  = 900
PULSE_INTERVAL   = 30
# ─────────────────────────────────────────────────────────────────────────────

logger = logging.getLogger(__name__)

# ─── LeviBrain singleton ──────────────────────────────────────────────────────
# Instantiated once at module load so every handle_mission call reuses the
# same in-memory state (memory, planner caches, evolution counters, etc.)
_brain_instance = None

def _get_brain():
    global _brain_instance
    if _brain_instance is None:
        from .brain import LeviBrain
        _brain_instance = LeviBrain()
        logger.info("🧠 [Orchestrator] LeviBrain singleton created.")
    return _brain_instance


class Orchestrator:
    """
    The Sovereign Mission Mainframe.
    Owns the full mission lifecycle: admission → brain → crystallization → audit.
    """

    def __init__(self):
        self.kernel_id      = KERNEL_ID
        self.start_time     = time.time()
        self._shutdown_evt  = asyncio.Event()
        self._active: Dict[str, MissionState] = {}
        self._lock          = asyncio.Lock()
        self._initialized   = False

        # ── Engine matrix (shared instances) ──────────────────────────────────
        self.memory     = MemoryManager()
        self.perception = PerceptionEngine(self.memory)
        self.planner    = DAGPlanner()
        self.executor   = GraphExecutor()
        self.reasoning  = ReasoningCore()
        self.world      = WorldModel()
        self.reflection = ReflectionEngine()
        self.evolution  = EvolutionaryIntelligenceEngine()
        self.identity   = identity_system
        self.failure    = FailurePolicyEngine()
        self.workflow   = WorkflowEngine()
        self.context    = ContextManager()
        self.learning   = LearningLoop()

        # ── Mesh / autonomy ────────────────────────────────────────────────────
        self.dcn        = dcn_registry.get_gossip()
        self.consensus  = get_dcn_mesh()
        self._metrics   = MetricsHub()
        self._sentinel  = None
        self._pulse     = None
        self.mesh_proto = None

        # ── Autonomy engines ───────────────────────────────────────────────────
        from backend.core.evolution.drift_detector import drift_detector
        from backend.agents.chaos import ChaosAgent
        self.drift_detector = drift_detector
        self.chaos_agent    = ChaosAgent(self)

        logger.info("🛰️  [Orchestrator] Instinctual init complete. Kernel: %s", self.kernel_id)

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    async def initialize(self) -> None:
        """Called from main.py lifespan — boot sequence."""
        await self.boot_sovereign_os()

    async def boot_sovereign_os(self) -> None:
        """Multi-stage OS boot."""
        logger.info("🧩 [Orchestrator] SOVEREIGN BOOT (%s)...", OS_VERSION)
        try:
            await self._calibrate_hardware()
            recovered = await CentralExecutionState.recover_active_missions()
            async with self._lock:
                for mid, state in recovered.items():
                    self._active[mid] = state
            logger.info("✅ [Orchestrator] Recovered %d mission states.", len(recovered))

            await self._establish_mesh()

            from backend.core.goal_engine import goal_engine
            goal_engine.orchestrator = self
            await goal_engine.start()

            from .self_healing import self_healing
            await self_healing.start()

            self._sentinel = asyncio.create_task(self._sentinel_worker())
            self._pulse    = asyncio.create_task(self._pulse_worker())
            asyncio.create_task(self.chaos_agent.ignite_storm())

            # Start kernel telemetry background tasks
            kernel.start_background_tasks()

            self._initialized = True
            logger.info("🚀 [Orchestrator] ONLINE. [%s]", OS_VERSION)
        except Exception as exc:
            logger.critical("🛑 [Orchestrator] BOOT FAILURE: %s", exc)
            raise RuntimeError(f"Sovereign boot failed: {exc}") from exc

    async def teardown_gracefully(self, timeout: int = 30) -> None:
        """Graceful shutdown — drain in-flight missions then stop workers."""
        logger.info("🛑 [Orchestrator] Graceful teardown (timeout=%ds)...", timeout)
        self._shutdown_evt.set()

        deadline = time.time() + timeout
        while self._active and time.time() < deadline:
            await asyncio.sleep(0.5)

        if self._sentinel and not self._sentinel.done():
            self._sentinel.cancel()
        if self._pulse and not self._pulse.done():
            self._pulse.cancel()

        logger.info("✅ [Orchestrator] Teardown complete. Remaining missions: %d", len(self._active))

    async def force_abort_all(self, reason: str) -> None:
        """Abort all active missions immediately (called on SIGTERM)."""
        logger.warning("⚠️  [Orchestrator] Force-aborting all missions. Reason: %s", reason)
        async with self._lock:
            for mid in list(self._active.keys()):
                self._active[mid].status = "ABORTED"
            self._active.clear()

    async def reboot_engine(self, agent_id: str) -> None:
        """Restart a named sub-engine (called by kernel on agent crash)."""
        logger.warning("🔄 [Orchestrator] Rebooting engine: %s", agent_id)
        # Future: call agent registry to restart the specific agent process.

    # ── Mission gateway ───────────────────────────────────────────────────────

    async def handle_mission(
        self,
        user_input:  str,
        user_id:     str,
        session_id:  str,
        streaming:   bool = False,
        **kwargs,
    ) -> Any:
        """
        Single authority for all mission orchestration.
        Perception → Brain → Crystallization → Audit → Mesh sync.
        """
        mission_id = kwargs.get("request_id") or f"mission-{uuid.uuid4().hex[:12]}"
        log_request_id.set(mission_id)
        log_user_id.set(user_id)
        log_session_id.set(session_id)

        start_ts = time.time()
        logger.info("🌀 [Orchestrator] Mission %s awakening (user=%s)", mission_id, user_id)

        # ── 1. Admission control ──────────────────────────────────────────────
        vram_pressure = await self.get_vram_pressure()
        if vram_pressure > VRAM_ADMISSION and not kwargs.get("force_admission"):
            logger.critical("🛑 [Resources] VRAM %.2f > threshold. Offloading.", vram_pressure)
            return await self._delegate_to_mesh(mission_id, user_id, user_input, session_id,
                                                "RESOURCE_BACKPRESSURE", **kwargs)

        # ── 2. Safety gate ────────────────────────────────────────────────────
        intercept = await self._safety_gate(user_id, user_input, mission_id)
        if intercept and intercept.get("action") == "REJECT":
            return intercept["result"]
        if intercept and intercept.get("action") == "BYPASS":
            user_input = intercept.get("new_input", user_input)

        # ── 3. Register mission ────────────────────────────────────────────────
        await self._register_mission(mission_id, user_id, user_input)

        try:
            # ── 3a. Graduation bypass (T0 fast-path) ──────────────────────────
            intent_type = await self.perception.classify_intent(user_input)
            bypass_rule = await graduation_service.get_bypass_rule(intent_type)
            if bypass_rule and bypass_rule.get("deterministic_response"):
                result = {
                    "response":  bypass_rule["deterministic_response"],
                    "intent":    intent_type,
                    "fidelity":  1.0,
                    "graduated": True,
                }
                await self._post_execute(mission_id, user_id, user_input, session_id,
                                         result, start_ts)
                return result
            if bypass_rule:
                kwargs.update(bypass_rule)

            # ── 3b. Mission admission (HAL-0 BFT gate) ────────────────────────
            admission = {
                "mission_id": mission_id,
                "user_id":    user_id,
                "input_hash": hashlib.sha256(user_input.encode()).hexdigest(),
            }
            admission = await graduation_service.admit_pulse(mission_id, admission)
            kwargs.update(admission)

            # ── 3c. Kernel resource reservation ──────────────────────────────
            kernel.schedule_mission(mission_id, "Normal")
            kernel.update_mission_state(mission_id, "Analyzing")

            # ── 4. Brain delegation ───────────────────────────────────────────
            brain = _get_brain()

            if streaming:
                return self._handle_stream(brain, user_input, user_id, session_id,
                                           mission_id, **kwargs)

            result = await brain.route(
                user_input=user_input,
                user_id=user_id,
                session_id=session_id,
                streaming=False,
                request_id=mission_id,
                **kwargs,
            )

            kernel.update_mission_state(mission_id, "Succeeded")

            # ── 5. Post-execution crystallization ──────────────────────────────
            await self._post_execute(mission_id, user_id, user_input, session_id,
                                     result, start_ts)
            return result

        except Exception as exc:
            logger.exception("🚑 [Orchestrator] Mission %s fault: %s", mission_id, exc)
            kernel.update_mission_state(mission_id, "Failed")
            MISSION_ABORTED.inc()
            await self._deregister_mission(mission_id)
            return await self._delegate_to_mesh(mission_id, user_id, user_input, session_id,
                                                str(exc), **kwargs)

    async def _post_execute(
        self,
        mission_id: str,
        user_id:    str,
        user_input: str,
        session_id: str,
        result:     Dict[str, Any],
        start_ts:   float,
    ) -> None:
        """Crystallization, learning, evolution, audit, mesh sync."""
        latency = (time.time() - start_ts) * 1000
        result["latency_mainframe_ms"] = latency

        # Closed-loop learning
        await self.learning.crystallize_pattern(
            mission_id=mission_id,
            query=user_input,
            result=str(result.get("response", "")),
            fidelity=result.get("fidelity", 1.0),
            metadata={
                "user_id":       user_id,
                "latency_ms":    latency,
                "intent_type":   result.get("intent", "chat"),
                "agent_sequence": result.get("agent_sequence", []),
            },
        )

        # Evolution ingestion
        await self.evolution.ingest_mission_outcome(
            mission_id=mission_id,
            input_data=user_input,
            output_data=result.get("response", ""),
            fidelity=result.get("fidelity", 0.95),
            agent_path=result.get("agent_sequence", []),
        )

        # Non-repudiable audit signature
        pulse_hash = await self._sign_pulse(mission_id, result)
        result["audit_sig"] = pulse_hash

        # Mesh propagation
        await self._propagate_to_mesh(mission_id, result)

        # Production monitoring
        try:
            from backend.services.monitoring import monitoring_service
            await monitoring_service.log_mission_metrics(
                mission_id=mission_id,
                fidelity=result.get("fidelity", 1.0),
                latency=latency,
                agent_count=len(result.get("agent_sequence", [])),
            )
        except Exception:
            pass  # monitoring is non-critical

        await self._deregister_mission(mission_id)
        MISSION_COMPLETED.inc()
        CognitiveTracer.end_trace(mission_id, "success", {"fidelity": result.get("fidelity", 1.0)})
        logger.info("✅ [Orchestrator] Mission %s done in %.1fms", mission_id, latency)

    # ── Streaming ─────────────────────────────────────────────────────────────

    async def _handle_stream(self, brain, inp, uid, sid, mid, **kwargs):
        """Wrap the Brain streaming generator in OS-level telemetry."""
        try:
            async for chunk in await brain.route(inp, uid, sid, streaming=True,
                                                  request_id=mid, **kwargs):
                yield chunk
            await self._deregister_mission(mid)
            MISSION_COMPLETED.inc()
        except Exception as exc:
            logger.error("🌊 [Orchestrator] Stream rupture %s: %s", mid, exc)
            yield {"event": "error", "data": "Cognitive stream interrupted."}
            await self._deregister_mission(mid)

    # ── Safety gate ───────────────────────────────────────────────────────────

    async def _safety_gate(self, user_id, user_input, mission_id) -> Optional[Dict]:
        raw = user_input.lower().strip()

        if "levi, execute" in raw or "levi execute" in raw:
            ctx_hash = self._fast_hash(user_id, user_input)
            cached = await state_bridge.get(f"confirm:{user_id}:{ctx_hash}")
            if cached:
                data = json.loads(cached)
                return {"action": "BYPASS", "new_input": data["original"]}

        risky = ["delete all", "wipe drive", "format", "shutdown sovereign",
                 "kill kernel", "factory reset"]
        if any(r in raw for r in risky):
            ctx_hash = self._fast_hash(user_id, user_input)
            await state_bridge.set(
                f"confirm:{user_id}:{ctx_hash}",
                json.dumps({"original": user_input}),
                ex=60,
            )
            return {
                "action": "REJECT",
                "result": {
                    "response": "Destructive command detected. Say 'Levi, Execute' to confirm.",
                    "status":   "AWAIT_CONFIRMATION",
                    "request_id": mission_id,
                },
            }
        return None

    def _fast_hash(self, uid, txt):
        return hashlib.sha256(f"{uid}:{txt[:60]}".encode()).hexdigest()[:8]

    # ── Audit ─────────────────────────────────────────────────────────────────

    async def _sign_pulse(self, mid: str, res: Dict) -> str:
        res_hash = hashlib.sha256(str(res.get("response", "")).encode()).hexdigest()
        payload = {
            "mid":    mid,
            "hash":   res_hash,
            "ts":     datetime.datetime.now(timezone.utc).isoformat(),
            "kernel": self.kernel_id,
            "os":     OS_VERSION,
        }
        return await SovereignKMS.sign_trace(json.dumps(payload))

    async def _propagate_to_mesh(self, mid: str, res: Dict) -> None:
        if self.mesh_proto and getattr(self.mesh_proto, "is_active", False):
            await self.mesh_proto.broadcast_gossip(mid, {"status": "success"}, "mission_complete")

    # ── State management ──────────────────────────────────────────────────────

    async def _register_mission(self, mid, uid, txt) -> None:
        async with self._lock:
            self._active[mid] = MissionState(mission_id=mid, user_id=uid, status="ADMITTED")
        redis = get_redis_client()
        if redis:
            redis.sadd(f"orchestrator:{self.kernel_id}:active", mid)

    async def _deregister_mission(self, mid) -> None:
        async with self._lock:
            self._active.pop(mid, None)
        redis = get_redis_client()
        if redis:
            redis.srem(f"orchestrator:{self.kernel_id}:active", mid)

    # ── Mesh failover ─────────────────────────────────────────────────────────

    async def _delegate_to_mesh(self, mid, uid, obj, sid, reason, **kwargs) -> Dict:
        logger.warning("🔄 [Mesh] Delegating %s → swarm. Reason: %s", mid, reason)
        return {
            "response":   f"Regional failover. Mission delegated: {reason}",
            "status":     "FAILOVER_MESH",
            "request_id": mid,
        }

    # ── Hardware calibration ──────────────────────────────────────────────────

    async def _calibrate_hardware(self) -> None:
        metrics = kernel.get_gpu_metrics()
        logger.info("🖥️  [Hardware] GPU: %s VRAM: %sMB",
                    metrics.get("gpu_name", "unknown"),
                    metrics.get("vram_total_mb", "?"))
        disk = shutil.disk_usage(os.getcwd())
        free_gb = disk.free / (1024 ** 3)
        if free_gb < 20:
            logger.warning("🚨 [Hardware] Low storage: %.1f GB free.", free_gb)

    async def _establish_mesh(self) -> None:
        from backend.core.dcn_protocol import get_dcn_protocol
        self.mesh_proto = get_dcn_protocol()
        if self.mesh_proto and getattr(self.mesh_proto, "is_active", False):
            logger.info("🛰️  [Mesh] Consensus established: %s", self.mesh_proto.node_id)
        else:
            logger.warning("📡 [Mesh] Isolate. Operating in REGIONAL MODE.")

    # ── Diagnostics (used by API layer) ──────────────────────────────────────

    async def get_vram_pressure(self) -> float:
        try:
            m = kernel.get_gpu_metrics()
            t = m.get("vram_total_mb", 8192)
            u = m.get("vram_used_mb", 0)
            return u / t if t > 0 else 0.0
        except Exception:
            return 0.0

    async def count_active_missions(self) -> int:
        return len(self._active)

    async def get_dcn_health(self) -> str:
        if self.mesh_proto and getattr(self.mesh_proto, "is_active", False):
            return "active"
        return "offline"

    async def get_system_health(self) -> Dict[str, Any]:
        vram = await self.get_vram_pressure()
        return {
            "version":        OS_VERSION,
            "kernel":         self.kernel_id,
            "graduation":     await self.get_graduation_score(),
            "status":         "STABLE" if vram < 0.9 else "CONSTRAINED",
            "active_missions": len(self._active),
            "uptime_sec":     int(time.time() - self.start_time),
        }

    async def get_graduation_score(self) -> float:
        score = 0.95
        if kernel.rust_kernel:
            score += 0.03
        if HAS_REDIS:
            score += 0.01
        success = MISSION_COMPLETED._value.get()
        fail    = MISSION_ABORTED._value.get()
        total   = success + fail
        if total > 0:
            score *= success / total
        final = min(1.0, score)
        GRADUATION_SCORE.set(final)
        return round(final, 3)

    # ── Sentinel & pulse workers ──────────────────────────────────────────────

    async def _sentinel_worker(self):
        logger.info("🛰️  [Sentinel] AWAKENED.")
        iteration = 0
        while not self._shutdown_evt.is_set():
            try:
                iteration += 1
                score = await self.get_graduation_score()

                from .self_healing import self_healing
                vram = await self.get_vram_pressure()
                if vram > 0.90:
                    logger.info("🩺 [Sentinel] High VRAM — invoking self-healer.")
                    await self_healing._heal_resource_exhaustion()

                if iteration % 30 == 0:
                    await self.memory.cull_decayed_memories(decay_factor=0.92)

                await self.identity.realign_biases()

                if iteration % 60 == 0:
                    embeddings = [self.identity.get_current_bias_vector()]
                    drift = await self.drift_detector.calculate_drift(embeddings)
                    logger.info("⚖️  [Sentinel] Epistemic drift: %.4f", drift)

                if iteration % 360 == 0:
                    await self.evolution.evolve_swarm()

                await asyncio.sleep(600 if score > 0.95 else 60)
            except Exception as exc:
                logger.error("⚠️  [Sentinel] Error: %s", exc)
                await asyncio.sleep(60)

    async def _pulse_worker(self):
        while not self._shutdown_evt.is_set():
            try:
                if self.mesh_proto and getattr(self.mesh_proto, "is_active", False):
                    await self.mesh_proto.broadcast_heartbeat(
                        self.kernel_id, await self.get_system_health()
                    )
            except Exception:
                pass
            await asyncio.sleep(PULSE_INTERVAL)

    async def _reset_hardware_pools(self):
        logger.info("🛠️  [Self-Healing] Flushing VRAM pools...")
        kernel.flush_vram_buffer()
        logger.info("✅ [Self-Healing] VRAM pools flushed.")


# ─── Module singletons ────────────────────────────────────────────────────────
orchestrator = Orchestrator()
_orchestrator = orchestrator          # ← main.py imports this name

async def run_mainframe(**kwargs) -> Any:
    return await orchestrator.handle_mission(**kwargs)
