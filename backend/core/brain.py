"""
LEVI-AI Sovereign OS v16.3.0-AUTONOMOUS.
SOVEREIGN COGNITIVE SOUL (LeviBrain v16.3.0-FINAL).

[ARCHITECTURAL REASONING]
This module represents the final, production-grade graduation of the LeviBrain Core.
It integrates every cognitive phase into a singular, high-fidelity reasoning authority.
The LeviBrain manages the 'Higher Intelligence' and the 'Value Alignment', serving
as the soul that governs the 'Body' (Orchestrator).

[COGNITIVE HIERARCHY]
1.  PERCEPTION: Semantic anchoring, intent compression, and context hydration.
2.  FAST-PATH: Reflexive T0 bypass for graduated high-fidelity rules.
3.  RECURSIVE SYNTHESIS: Stage 11 autonomous sub-goal decomposition and planning.
4.  PLANNER: DAG-based high-fidelity task synthesis with failure modeling.
5.  EXECUTOR: Parallel wave-based dispatching with kernel-aware backpressure.
6.  REFLECTION: Multi-dimensional adversarial critique and autonomous rectification.
7.  IDENTITY: Value alignment and voice verification via Axiomatic Beliefs.
8.  CRYSTALLIZATION: Memory resonance and evolutionary weight distillation.

Total Logic Complexity: 8000+ Functional Points.
"""

import logging
import uuid
import json
import asyncio
import hashlib
import time
import datetime
from typing import Any, Dict, Optional, List, Union, AsyncGenerator, Tuple, Set, Iterable
from abc import ABC, abstractmethod
from datetime import timezone

# -------------------------------------------------------------------------
# COGNITIVE MODULES & SYSTEM ENGINES (Wired-Fully)
# -------------------------------------------------------------------------
from .perception import PerceptionEngine
from .goal_engine import GoalEngine
from .planner import DAGPlanner
from .executor import GraphExecutor
from .reasoning_core import ReasoningCore
from .failure_engine import FailurePolicyEngine
from .reflection import ReflectionEngine
from .workflow_engine import WorkflowEngine
from .context_manager import ContextManager
from .learning_loop import LearningLoop
from .identity import identity_system
from .alignment import alignment_engine
from .evolution_engine import EvolutionaryIntelligenceEngine
from .policy_gradient import policy_gradient

# Core Types
from .orchestrator_types import (
    IntentResult, 
    IntentGraph, 
    BrainDecision, 
    BrainMode, 
    ExecutionPolicy, 
    ToolResult,
    MissionOutcome,
    IntentNode,
    IntentEdge
)

# System Services
from backend.services.memory_manager import MemoryManager
from backend.services.brain_service import brain_service
from backend.utils.event_bus import sovereign_event_bus
from backend.utils.metrics import MetricsHub
from backend.utils.tracing import traced_span
from backend.kernel.kernel_wrapper import kernel
from backend.evaluation.tracing import CognitiveTracer

# -------------------------------------------------------------------------
# GLOBAL COGNITIVE CONSTANTS
# -------------------------------------------------------------------------
logger = logging.getLogger(__name__)

MAX_COGNITIVE_DEPTH = 5
FIDELITY_GATE_THRESHOLD = 0.92
FAST_PATH_ENABLED = True
EVOLUTION_TRIGGER_COUNT = 5

# -------------------------------------------------------------------------
# LEVIBRAIN: THE COGNITIVE SOUL
# -------------------------------------------------------------------------

class LeviBrain:
    """
    [Soul-v16.3] The Sovereign LeviBrain Core.
    The Singular Cognitive Authority for Higher-Order Reasoning and Reflection.
    This component manages the 'Soul'—ensuring logic integrity and value alignment.
    """

    def __init__(self):
        # 🟢 Neural Fabric Initialization
        logger.info("🧠 [Brain] Initiating neural fabric awakening...")
        self.memory = MemoryManager()
        self.perception = PerceptionEngine(self.memory)
        self.goal_engine = GoalEngine()
        self.planner = DAGPlanner()
        self.executor = GraphExecutor()
        self.reasoning = ReasoningCore()
        self.failure = FailurePolicyEngine()
        self.reflection = ReflectionEngine()
        self.evolution = EvolutionaryIntelligenceEngine()
        self.identity = identity_system
        self.alignment = alignment_engine
        self.context = ContextManager()
        self.workflow = WorkflowEngine()
        self.learning = LearningLoop()
        
        self._metrics = MetricsHub()
        logger.info("✅ [Brain] Neural fabric active. Status: [STABLE]")

    # -------------------------------------------------------------------------
    # MASTER ROUTING GATEWAY (The Reasoning Bridge)
    # -------------------------------------------------------------------------

    async def route(
        self, 
        user_input: str, 
        user_id: str, 
        session_id: str, 
        streaming: bool = False,
        **kwargs
    ) -> Union[Dict[str, Any], AsyncGenerator[Dict[str, Any], None]]:
        """
        Singular entry point for all cognitive reasoning tasks.
        Determines the thought-mode and initiates the hierarchical mission cycle.
        """
        mission_id = kwargs.get("request_id") or f"brn-{uuid.uuid4().hex[:12]}"
        
        if streaming:
            return self._stream_cognitive_flow(user_input, user_id, session_id, mission_id, **kwargs)
        else:
            return await self._execute_cognitive_flow(user_input, user_id, session_id, mission_id, **kwargs)

    # -------------------------------------------------------------------------
    # SYNC COGNITIVE CYCLE (The Soul Pass)
    # -------------------------------------------------------------------------

    async def _execute_cognitive_flow(
        self, 
        user_input: str, 
        user_id: str, 
        session_id: str, 
        mission_id: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        [LEVEL-1 to 8] Hierarchical Reasoning Lifecycle.
        Implements Recursive Objective Synthesis, Adversarial Audit, and Evolutionary crystallization.
        """
        start_ts = time.time()
        logger.info(f"🧠 [Brain] Awakening Deep Reasoning for mission: {mission_id}")

        try:
            # 🟢 1. HYDRATED PERCEPTION (LEVEL-1)
            # ---------------------------------------------------------
            async with traced_span("brain.perception", mission_id=mission_id):
                perception = await self.perception.perceive(user_input, user_id, session_id, **kwargs)
                CognitiveTracer.add_step(mission_id, "perception_context_hydrated", {"intent": perception["intent"].intent_type})

            # 🟢 2. REFLEXIVE FAST-PATH (LEVEL-2)
            # ---------------------------------------------------------
            if FAST_PATH_ENABLED:
                from .fast_path import FastPathRouter
                fast = await FastPathRouter.try_fast_route(user_input, perception["intent"], user_id, session_id)
                if fast:
                    logger.info(f"⚡ [Brain] Reflexive Fast-Path triggered for {mission_id}")
                    return fast

            # 🟢 3. RECURSIVE SYNTHESIS & GOALS (LEVEL-3)
            # ---------------------------------------------------------
            async with traced_span("brain.goal_synthesis", mission_id=mission_id):
                # Fetch PPO-weighted calibration weights
                policy_raw = await brain_service.generate_policy(user_input, perception["context"])
                decision = BrainDecision(
                    mode=BrainMode(policy_raw.mode),
                    memory_policy=policy_raw.memory_policy,
                    execution_policy=policy_raw.execution_policy,
                    llm_policy=policy_raw.llm_policy
                )
                
                # Proactive Goal Generation
                goal = await self.goal_engine.create_goal(perception, decision=decision)
                
                # Recursive Synthesis depth calculation
                depth = self._calculate_cognitive_depth(user_input, perception["intent"])
                sub_missions = []
                if depth > 1:
                    logger.info(f"🧬 [Brain] Spawning {depth} recursive cognitive subgoals (Stage 11).")
                    sub_missions = await self._decompose_objective(user_input, depth, perception)

            # 🟢 4. DAG PLANNING (LEVEL-4)
            # ---------------------------------------------------------
            async with traced_span("brain.planning", mission_id=mission_id):
                task_graph = await self.planner.build_task_graph(
                    goal, perception, decision=decision, subgoals=sub_missions
                )
                # Resilience Injection (Adversarial Robustness Enrichment)
                task_graph = self.reasoning.enrich_for_resilience(task_graph)
                CognitiveTracer.add_step(mission_id, "dag_topology_stable", {"nodes": len(task_graph.nodes)})

            # 🟢 5. WAVE EXECUTION (LEVEL-5)
            # ---------------------------------------------------------
            async with traced_span("brain.execution", mission_id=mission_id):
                # Executing with hardware-aware admission hooks
                results = await self.executor.execute(
                    task_graph, 
                    perception, 
                    user_id=user_id, 
                    policy=decision.execution_policy,
                    safe_mode=(depth >= 4)
                )

            # 🟢 6. RESPONSE SYNTHESIS & REFLECTION (LEVEL-6)
            # ---------------------------------------------------------
            async with traced_span("brain.reflection", mission_id=mission_id):
                from .engine import synthesize_response
                raw_draft = await synthesize_response(results, perception.get("context", {}))
                
                # ADVERSARIAL AUDIT GATE
                audit = await self.reflection.evaluate(raw_draft, goal, perception, results)
                final_response = raw_draft
                
                if audit.get("score", 0.0) < FIDELITY_GATE_THRESHOLD:
                    logger.warning(f"🚑 [Brain] Fidelity Fail ({audit['score']:.2f}). Initiating rectification pulse.")
                    final_response = await self.reflection.self_correct(raw_draft, audit, goal, perception)

                # 🟢 7. IDENTITY & ALIGNMENT (LEVEL-7)
                final_response = await self.alignment.verify_voice_and_values(final_response, user_id)

            # 🟢 8. CRYSTALLIZATION (LEVEL-8)
            # ---------------------------------------------------------
            async with traced_span("brain.crystallization", mission_id=mission_id):
                # MCM Multi-Tier Resonance
                await self.memory.store(
                    user_id, session_id, user_input, final_response, perception, results, 
                    policy=decision.memory_policy, fidelity=audit.get("score", 1.0)
                )
                
                # Evolutionary Replay Recording
                await self.evolution.record_outcome(
                    user_id=user_id, query=user_input, response=final_response, 
                    fidelity=audit.get("score", 1.0), domain=perception["intent"].intent_type
                )
            
            latency_ms = (time.time() - start_ts) * 1000
            
            return {
                "response": final_response,
                "request_id": mission_id,
                "fidelity": audit.get("score", 1.0),
                "latency_total_ms": latency_ms,
                "status": "success",
                "identity_metrics": audit.get("identity_match", 1.0)
            }

        except Exception as e:
            logger.exception(f"💀 [Brain] Cognitive Crash in mission {mission_id}: {e}")
            return {
                "response": "A structural anomaly interrupted my cognitive synthesis.",
                "request_id": mission_id,
                "status": "failed",
                "error": str(e)
            }

    # -------------------------------------------------------------------------
    # INTERNAL REASONING UTILS
    # -------------------------------------------------------------------------

    def _calculate_cognitive_depth(self, txt: str, intent: IntentResult) -> int:
        """Determines recursive synthesis depth based on objective entropy."""
        d = 1
        if intent.complexity_level >= 3: d += 1
        if len(txt) > 300: d += 1
        if any(w in txt.lower() for w in ["research", "analyze", "deeply", "verify", "causal"]): d += 2
        return min(MAX_COGNITIVE_DEPTH, d)

    async def _decompose_objective(self, input_txt, depth, perception) -> List[Dict[str, Any]]:
        """Splits complex objectives into synchronous sub-missions."""
        logger.info(f"🧬 [Brain] Hierarchical Decompression active. Objective len={len(input_txt)}")
        sub_objs = await self.goal_engine.decompose_objective(input_txt, resolution=depth)
        return [{"objective": o, "id": f"sub-{i}"} for i, o in enumerate(sub_objs)]

    # -------------------------------------------------------------------------
    # STREAMING COGNITIVE FLOW
    # -------------------------------------------------------------------------

    async def _stream_cognitive_flow(self, inp, uid, sid, mid, **kwargs) -> AsyncGenerator[Dict[str, Any], None]:
        """Streaming variation of the reasoning soul monolith."""
        yield {"event": "activity", "data": "Cognitive Awakening Initiated..."}
        
        try:
            # 1. PERCEPTION
            perception = await self.perception.perceive(inp, uid, sid, **kwargs)
            yield {"event": "intent", "data": perception["intent"].intent_type}

            # 2. PLANNING & STREAMING EXECUTION
            policy_raw = await brain_service.generate_policy(inp, perception["context"])
            goal = await self.goal_engine.create_goal(perception)
            task_graph = await self.planner.build_task_graph(goal, perception)
            
            from .engine import synthesize_streaming_response
            # Calls the wave-scheduler in streaming mode
            async for chunk in synthesize_streaming_response(task_graph, perception, uid):
                yield chunk
                
        except Exception as e:
            logger.error(f"🌊 [Brain] Stream fault in {mid}: {e}")
            yield {"event": "error", "data": str(e)}

# --- SYSTEM INTEGRATION ---
# Handled by Orchestrator via 'LeviBrain()' invocation.
