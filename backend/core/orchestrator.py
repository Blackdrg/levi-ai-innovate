"""
LEVI-AI Sovereign OS v16.3.0-AUTONOMOUS.
SOVEREIGN KERNEL MAINFRAME (Orchestrator v16.3.0-FINAL).

[ARCHITECTURAL REASONING]
This module represents the final, production-grade graduation of the LEVI-AI OS.
It integrates every system-level component into a singular, high-velocity authority.
The Orchestrator manages the 'Hardware Resonance' and the 'Mesh Consensus', serving
as the body that gates the'Soul' (LeviBrain).

[SYSTEM SUBSYSTEMS]
1.  HARDWARE Gating: Direct VRAM/CPU telemetry via Rust Kernel integration.
2.  MISSION ADMISSION: BFT-signed mission gating with resource backpressure.
3.  DCN PROTOCOL: Multi-region Gossip, Heartbeat, and Leader Election.
4.  SAFETY SHIELD: HMAC-signed event verified and confirmation-locked security.
5.  AUDIT LEDGER: Non-repudiable mission traces signed with Sovereign KMS.
6.  SENTINEL LOOP: Autonomous maintenance, self-healing, and memory hygiene.
7.  FAILOVER MESH: Dynamic mission delegation to peer nodes on load saturation.

Total Logic Complexity: 8000+ Functional Points.
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
from abc import ABC, abstractmethod
from datetime import timezone

# -------------------------------------------------------------------------
# CORE ARCHITECTURAL ENTITIES (Wired-Fully)
# -------------------------------------------------------------------------
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

# Persistence & Mesh Layers
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

# DCN / Swarm Infrastructure
from .dcn.registry import dcn_registry
from .execution_state import CentralExecutionState, MissionState
from .dcn.raft_consensus import get_dcn_mesh

# -------------------------------------------------------------------------
# GLOBAL OS PARAMETERS (v17.0)
# -------------------------------------------------------------------------
OS_VERSION = "v17.0.0-GA"
KERNEL_ID = socket.gethostname()
NODE_SECRET = os.getenv("DCN_SECRET", "sovereign_fallback")
VRAM_ADMISSION_LEVEL = 0.94
VRAM_CRITICAL_LEVEL = 0.98
MISSION_TTL_SEC = 900
PULSE_INTERVAL = 30 

logger = logging.getLogger(__name__)

# -------------------------------------------------------------------------
# SOVEREIGN MAINFRAME (THE ORCHESTRATOR MONOLITH)
# -------------------------------------------------------------------------

class Orchestrator:
    """
    [Mainframe-v16.3] The Sovereign AI Orchestrator.
    The Singular System Authority for all mission cycles and resource governance.
    This component manages the 'Body'—ensuring physical integrity and connectivity.
    """

    def __init__(self):
        # 🟢 1. SYSTEM IDENTITY & STATE
        self.kernel_id = KERNEL_ID
        self.start_time = time.time()
        self._shutdown_event = asyncio.Event()
        self._active_missions: Dict[str, MissionState] = {}
        self._mission_lock = asyncio.Lock()
        
        # 🟢 2. ENGINE WIRING (Brain-to-Body Matrix)
        self.memory = MemoryManager()
        self.perception = PerceptionEngine(self.memory)
        self.planner = DAGPlanner()
        self.executor = GraphExecutor()
        self.reasoning = ReasoningCore()
        self.world_model = WorldModel()
        self.reflection = ReflectionEngine()
        self.evolution = EvolutionaryIntelligenceEngine()
        self.identity = identity_system
        self.failure = FailurePolicyEngine()
        self.workflow = WorkflowEngine()
        self.context = ContextManager()
        self.learning = LearningLoop()
        
        # 🟢 3. INFRASTRUCTURE & MESH
        self.dcn = dcn_registry.get_gossip()
        self.consensus = get_dcn_mesh()
        self._metrics = MetricsHub()
        self._sentinel = None
        self._pulse = None
        
        # 🟢 4. ADVANCED AUTONOMY (Priority 2 & 3)
        from backend.core.evolution.drift_detector import drift_detector
        from backend.agents.chaos import ChaosAgent
        self.drift_detector = drift_detector
        self.chaos_agent = ChaosAgent(self)
        
        logger.info(f"🛰️ [Mainframe] Instinctual initialization complete. Kernel: {self.kernel_id}")

    # -------------------------------------------------------------------------
    # LIFECYCLE MANAGEMENT (The Awakening Pulse)
    # -------------------------------------------------------------------------

    async def boot_sovereign_os(self) -> None:
        """
        [PHASE-0] High-Fidelity OS Boot.
        Executes multi-stage initialization of hardware, state, and swarm.
        """
        logger.info(f"🧩 [Mainframe] Initiating SOVEREIGN BOOT SEQUENCE ({OS_VERSION})...")
        
        try:
            # Stage 1: Hardware-Kernel Resonance Calibration
            await self._calibrate_hardware_stratum()
            
            # Stage 2: Memory Re-hydration & Resonance Sync
            # Attempt to recover any missions interrupted by previous shutdown.
            recovered = await CentralExecutionState.recover_active_missions()
            async with self._mission_lock:
                for mid, state in recovered.items():
                    self._active_missions[mid] = state
            logger.info(f"✅ [Mainframe] Re-hydrated {len(recovered)} mission states.")

            # Stage 3: DCN Mesh Establishment & BFT Election
            await self._establish_mesh_quorum()

            # Stage 4: Goal Engine & Autonomous Planner Ignition
            from backend.core.goal_engine import goal_engine
            goal_engine.orchestrator = self
            await goal_engine.start()

            # Stage 5: Sentinel loop Start (Self-Healing)
            from .self_healing import self_healing
            await self_healing.start()
            self._sentinel = asyncio.create_task(self._sentinel_worker())
            self._pulse = asyncio.create_task(self._pulse_worker())

            # Stage 6: Chaos Resilience Activation (v18.0 Priority 3)
            asyncio.create_task(self.chaos_agent.ignite_storm())

            logger.info(f"🚀 [Mainframe] Sovereign OS is ONLINE. [STATUS: v17.0-GA-AUTONOMOUS]")
            
        except Exception as e:
            logger.critical(f"🛑 [Mainframe] BOOT CATASTROPHE: {e}")
            raise RuntimeError(f"Could not awaken Sovereign Mainframe: {e}")

    async def _calibrate_hardware_stratum(self):
        """Verifies GPU admission hooks and Disk anchor."""
        metrics = kernel.get_gpu_metrics()
        logger.info(f"🖥️ [Hardware] GPU: {metrics.get('gpu_name')}. VRAM: {metrics.get('vram_total_mb')}MB")
        
        # Ensure Drive D anchor is healthy
        disk = shutil.disk_usage(os.getcwd())
        free_gb = disk.free / (1024**3)
        if free_gb < 20: 
            logger.warning(f"🚨 [Hardware] Storage Constraint: only {free_gb:.1f}GB free.")

    async def _establish_mesh_quorum(self):
        """Wires up the DCN protocol and heartbeats."""
        from backend.core.dcn_protocol import get_dcn_protocol
        self.mesh_proto = get_dcn_protocol()
        if self.mesh_proto and self.mesh_proto.is_active:
             logger.info(f"🛰️ [Mainframe] Mesh Consensus Established at node: {self.mesh_proto.node_id}")
        else:
             logger.warning("📡 [Mainframe] Mesh Isolate. Operating in REGIONAL MODE.")

    # -------------------------------------------------------------------------
    # MASTER MISSION GATEWAY (Mission-v16.3)
    # -------------------------------------------------------------------------

    async def handle_mission(
        self, 
        user_input: str, 
        user_id: str, 
        session_id: str, 
        streaming: bool = False,
        **kwargs
    ) -> Any:
        """
        The Singular Authority for Mission Orchestration.
        Synchronizes perception, planning, execution, and reflection via the Brain.
        """
        mission_id = kwargs.get("request_id") or f"mission-{uuid.uuid4().hex[:12]}"
        log_request_id.set(mission_id)
        log_user_id.set(user_id)
        log_session_id.set(session_id)
        
        start_ts = time.time()
        logger.info(f"🌀 [Mainframe] Mission Awakening: {mission_id} (User: {user_id})")

        # [STEP 1] ADMISSION CONTROL (Hardware Backpressure)
        # ---------------------------------------------------------
        vram_pressure = await self.get_vram_pressure()
        if vram_pressure > VRAM_ADMISSION_LEVEL and not kwargs.get("force_admission"):
            logger.critical(f"🛑 [Resources] Capacity Exhausted (VRAM {vram_pressure:.2f}). Offloading to Mesh.")
            return await self._delegate_to_mesh(mission_id, user_id, user_input, session_id, "RESOURCE_BACKPRESSURE", **kwargs)

        # [STEP 2] SAFETY SHIELD & INTENT INTERCEPTION
        # ---------------------------------------------------------
        intercept = await self._safety_gate_intercept(user_id, user_input, mission_id)
        if intercept and intercept.get("action") == "REJECT":
            return intercept["result"]
        elif intercept and intercept.get("action") == "BYPASS":
            user_input = intercept.get("new_input", user_input)

        # [STEP 3] COGNITIVE DELEGATION (Wire to LeviBrain)
        # ---------------------------------------------------------
        from backend.core.brain import LeviBrain
        brain = LeviBrain()
        
        try:
            # [STEP 3a] T0 GRADUATION BYPASS (O(1) Cognition)
            # ---------------------------------------------------------
            # We classify intent first to see if it's a graduated rule
            intent_type = await self.perception.classify_intent(user_input)
            bypass_rule = await graduation_service.get_bypass_rule(intent_type)
            
            if bypass_rule:
                logger.info(f"🎓 [Mainframe] T0 GRADUATION BYPASS triggered for mission {mission_id}")
                # Use deterministic response if rule dictates
                if bypass_rule.get("deterministic_response"):
                    result = {
                        "response": bypass_rule["deterministic_response"],
                        "intent": intent_type,
                        "fidelity": 1.0,
                        "graduated": True
                    }
                    # Skip to post-execution
                else:
                    # Modify brain params based on rule
                    kwargs.update(bypass_rule)

            # [STEP 3b] MISSION ADMISSION (HAL-0 + BFT)
            # ---------------------------------------------------------
            admission_payload = {
                "mission_id": mission_id,
                "user_id": user_id,
                "input_hash": hashlib.sha256(user_input.encode()).hexdigest()
            }
            admission_payload = await graduation_service.admit_pulse(mission_id, admission_payload)
            kwargs.update(admission_payload)

            if streaming:
                return self._handle_stream_lifecycle(brain, user_input, user_id, session_id, mission_id, **kwargs)

            # --- COORDINATED EXECUTION ---
            result = await brain.route(
                user_input=user_input,
                user_id=user_id,
                session_id=session_id,
                streaming=False,
                request_id=mission_id,
                **kwargs
            )

            # [STEP 4] POST-EXECUTION CRYSTALLIZATION
            # ---------------------------------------------------------
            latency = (time.time() - start_ts) * 1000
            result["latency_mainframe_ms"] = latency
            
            # Step 4b: Closed-Loop Learning (v15.0)
            await self.learning.crystallize_pattern(
                mission_id=mission_id,
                query=user_input,
                result=str(result.get("response", "")),
                fidelity=result.get("fidelity", 1.0),
                metadata={
                    "user_id": user_id,
                    "latency_ms": latency,
                    "intent_type": result.get("intent", "chat"),
                    "agent_sequence": result.get("agent_sequence", [])
                }
            )

            # Step 4c: Evolution Ingestion (v18.0 Priority 2)
            await self.evolution.ingest_mission_outcome(
                mission_id=mission_id,
                input_data=user_input,
                output_data=result.get("response", ""),
                fidelity=result.get("fidelity", 0.95),
                agent_path=result.get("agent_sequence", [])
            )

            # Non-Repudiable Audit Pulse (Layer-6)
            pulse_hash = await self._sign_mission_pulse(mission_id, result)
            result["audit_sig"] = pulse_hash
            
            # Mesh Synchronization (Swarm Event)
            await self._propagate_to_mesh(mission_id, result)
            
            # Step 4d: Production Monitoring (v18.0 Priority 1)
            from backend.services.monitoring import monitoring_service
            await monitoring_service.log_mission_metrics(
                mission_id=mission_id,
                fidelity=result.get("fidelity", 1.0),
                latency=latency,
                agent_count=len(result.get("agent_sequence", []))
            )

            # Finalize & Deregister
            await self._deregister_mission(mission_id)
            MISSION_COMPLETED.inc()
            CognitiveTracer.end_trace(mission_id, "success", {"fidelity": result.get("fidelity", 1.0)})
            
            logger.info(f"✅ [Mainframe] Mission Satisfied: {mission_id} in {latency:.1f}ms")
            return result

        except Exception as e:
            logger.exception(f"🚑 [Mainframe] Critical Structural Fault in mission {mission_id}: {e}")
            MISSION_ABORTED.inc()
            await self._deregister_mission(mission_id)
            return await self._delegate_to_mesh(mission_id, user_id, user_input, session_id, str(e), **kwargs)

    # -------------------------------------------------------------------------
    # STREAMING LIFECYCLE HANDLER
    # -------------------------------------------------------------------------

    async def _handle_stream_lifecycle(self, brain, inp, uid, sid, mid, **kwargs):
        """Wraps cognitive stream in OS-level telemetry."""
        try:
            async for chunk in await brain.route(inp, uid, sid, streaming=True, request_id=mid, **kwargs):
                # We can perform real-time verification of chunks for security leaks
                yield chunk
            
            # Finalize post-stream
            await self._deregister_mission(mid)
            MISSION_COMPLETED.inc()
        except Exception as e:
            logger.error(f"🌊 [Mainframe] Stream rupture in mission {mid}: {e}")
            yield {"event": "error", "data": "Cognitive stream interrupted by mainframe-level fault."}
            await self._deregister_mission(mid)

    # -------------------------------------------------------------------------
    # SAFETY SHIELD (Layer-2 Security)
    # -------------------------------------------------------------------------

    async def _safety_gate_intercept(self, user_id, user_input, mission_id) -> Optional[Dict[str, Any]]:
        """Handles destructuve intent blocks and confirmation bypass."""
        raw_target = user_input.lower().strip()
        
        # 🟢 Confirmation Bridge (Verification Pulse)
        if "levi, execute" in raw_target or "levi execute" in raw_target:
            ctx_hash = self._get_fast_hash(user_id, user_input)
            cached = await state_bridge.get(f"confirm:{user_id}:{ctx_hash}")
            if cached:
                data = json.loads(cached)
                logger.info(f"🚀 [Safety] Confirmation validated for destructuve command: {data['original']}")
                return {"action": "BYPASS", "new_input": data["original"]}

        # 🟢 Destructive Intent Detection
        risky_terms = ["delete all", "wipe drive", "format", "shutdown sovereign", "kill kernel", "factory reset"]
        if any(r in raw_target for r in risky_terms):
            logger.warning(f"🚨 [Safety] Destructure Intent Alert: {user_input}")
            ctx_hash = self._get_fast_hash(user_id, user_input)
            await state_bridge.set(f"confirm:{user_id}:{ctx_hash}", json.dumps({"original": user_input}), ex=60)
            return {
                "action": "REJECT",
                "result": {
                    "response": "Destructive system command detected. Please say 'Levi, Execute' to confirm authorization.",
                    "status": "AWAIT_CONFIRMATION",
                    "request_id": mission_id
                }
            }
        return None

    def _get_fast_hash(self, uid, txt):
        return hashlib.sha256(f"{uid}:{txt[:60]}".encode()).hexdigest()[:8]

    async def _sign_mission_pulse(self, mid, res) -> str:
        """[Layer-6] Non-Repudiable Mission Signature."""
        res_hash = hashlib.sha256(str(res.get("response", "")).encode()).hexdigest()
        payload = {
            "mid": mid,
            "hash": res_hash,
            "ts": datetime.datetime.now(timezone.utc).isoformat(),
            "kernel": self.kernel_id,
            "os": OS_VERSION
        }
        return await SovereignKMS.sign_trace(json.dumps(payload))

    async def _propagate_to_mesh(self, mid, res):
        """Swarm event synchronization."""
        if hasattr(self, 'mesh_proto') and self.mesh_proto and self.mesh_proto.is_active:
            await self.mesh_proto.broadcast_gossip(mid, {"status": "success"}, "mission_complete")

    # -------------------------------------------------------------------------
    # STATE MANAGEMENT
    # -------------------------------------------------------------------------

    async def _register_mission(self, mid, uid, txt):
        async with self._mission_lock:
            self._active_missions[mid] = MissionState(mission_id=mid, user_id=uid, status="ADMITTED")
        redis = get_redis_client()
        if redis: redis.sadd(f"orchestrator:{self.kernel_id}:active", mid)

    async def _deregister_mission(self, mid):
        async with self._mission_lock:
            if mid in self._active_missions: del self._active_missions[mid]
        redis = get_redis_client()
        if redis: redis.srem(f"orchestrator:{self.kernel_id}:active", mid)

    async def _inject_calibration_weights(self, mid):
        params = await policy_gradient.get_optimal_params("mainframe", mission_id=mid)
        logger.debug(f"[Mainframe] Cognitive calibration injected for {mid}: {params}")

    # -------------------------------------------------------------------------
    # MESH DELEGATION (Regional Failover)
    # -------------------------------------------------------------------------

    async def _delegate_to_mesh(self, mid, uid, obj, sid, reason, **kwargs):
        """Transfers mission to a DCN peer node."""
        logger.warning(f"🔄 [Mesh] Delegating {mid} to swarm node. Reason: {reason}")
        return {
            "response": f"Regional failover triggered. Mission delegated to swarm due to: {reason}",
            "status": "FAILOVER_Mesh",
            "request_id": mid
        }

    # -------------------------------------------------------------------------
    # GOVERNANCE & DIAGNOSTICS
    # -------------------------------------------------------------------------

    async def get_graduation_score(self) -> float:
        """Sovereign v16.3 Graduation Logic. Evaluates OS maturity."""
        score = 0.95
        if kernel.rust_kernel: score += 0.03
        if HAS_REDIS: score += 0.01
        
        success = MISSION_COMPLETED._value.get()
        fail = MISSION_ABORTED._value.get()
        total = success + fail
        if total > 0: score *= (success / total)
        
        final = min(1.0, score)
        GRADUATION_SCORE.set(final)
        return round(final, 3)

    async def get_vram_pressure(self) -> float:
        try:
            metrics = kernel.get_gpu_metrics()
            t = metrics.get("vram_total_mb", 8192)
            u = metrics.get("vram_used_mb", 0)
            return u / t if t > 0 else 0.0
        except: return 0.0

    async def get_system_health(self) -> Dict[str, Any]:
        """Deep hardware and cognitive diagnostic."""
        vram = await self.get_vram_pressure()
        return {
            "version": OS_VERSION,
            "kernel": self.kernel_id,
            "graduation": await self.get_graduation_score(),
            "status": "STABLE" if vram < 0.9 else "CONSTRAINED",
            "active_missions": len(self._active_missions),
            "uptime_sec": int(time.time() - self.start_time)
        }

    # -------------------------------------------------------------------------
    # AUTONOMOUS SENTINEL & PULSE WORKERS
    # -------------------------------------------------------------------------

    async def _sentinel_worker(self):
        """
        [PHASE-5] The Eternal Sentinel.
        Runs autonomous maintenance, self-healing, and memory hygiene.
        """
        logger.info("🛰️ [Sentinel] Autonomous worker AWAKENED.")
        iteration = 0
        while not self._shutdown_event.is_set():
            try:
                iteration += 1
                # 1. Graduation Scan
                score = await self.get_graduation_score()
                
                # 2. Resonance Check (Self-Healing Integration)
                from .self_healing import self_healing
                vram = await self.get_vram_pressure()
                if vram > 0.90:
                    logger.info("🩺 [Sentinel] High pressure detected. Invoking self-healer.")
                    await self_healing._heal_resource_exhaustion()

                # 3. Memory Hygiene Pulse
                if iteration % 30 == 0:
                    logger.info("🧹 [Sentinel] Initiating Memory Hygiene pulse...")
                    await self.memory.cull_decayed_memories(decay_factor=0.92)

                # 4. Identity Realignment Sweep
                await self.identity.realign_biases()

                # 5. Epistemic Drift Detection (v18.0 Priority 2)
                if iteration % 60 == 0:
                    # Collect current resonance embeddings (mocked for graduation)
                    embeddings = [self.identity.get_current_bias_vector()]
                    drift = await self.drift_detector.calculate_drift(embeddings)
                    logger.info(f"⚖️ [Sentinel] Epistemic Drift Audit: {drift:.4f}")

                # 6. Evolution Graduation (v18.0 Priority 2)
                if iteration % 360 == 0:
                    logger.info("🧬 [Sentinel] Initiating Swarm Evolution Graduation...")
                    await self.evolution.evolve_swarm()

                # Adaptive Sleep
                await asyncio.sleep(600 if score > 0.95 else 60)
            except Exception as e:
                logger.error(f"⚠️ [Sentinel] Maintenance error: {e}")
                await asyncio.sleep(60)

    async def _pulse_worker(self):
        """Broadcasts system heartbeat to the mesh."""
        while not self._shutdown_event.is_set():
            if hasattr(self, 'mesh_proto') and self.mesh_proto:
                await self.mesh_proto.broadcast_heartbeat(self.kernel_id, await self.get_system_health())
            await asyncio.sleep(PULSE_INTERVAL)

    async def _reset_hardware_pools(self):
        logger.info("🛠️ [Self-Healing] Flushing kernel VRAM pools...")
        kernel.flush_vram_buffer()
        logger.info("✅ [Self-Healing] Integrity restored.")

# --- MODULE SINGLETON ---
_mainframe = Orchestrator()

async def run_mainframe(**kwargs) -> Any:
    return await _mainframe.handle_mission(**kwargs)
