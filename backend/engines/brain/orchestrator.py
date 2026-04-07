import asyncio
import logging
import time
from .planner import BrainPlanner
from .pipeline import FlowState, FlowPipeline
from backend.core.agent_registry import AgentRegistry
from backend.engines.utils.security import SovereignSecurity
from backend.engines.utils.i18n import SovereignI18n
from backend.utils.audit import AuditLogger

logger = logging.getLogger(__name__)

class BrainOrchestrator:
    """
    Sovereign Orchestration Core v7.
    Manages the lifecycle of a query via the Global Agent Registry.
    """
    
    def __init__(self):
        self.planner = BrainPlanner()

    async def stream_request(self, user_id: str, query: str, lang: str = "en"):
        """
        Final Production-Grade Orchestration Stream.
        """
        logger.info(f"Sovereign Mission initiated: {user_id}")
        
        # 1. Security Input Scrubbing
        query = SovereignSecurity.mask_pii(query, user_id=user_id)
        if SovereignSecurity.detect_injection(query):
            yield {"event": "error", "data": "Security violation detected."}
            return

        state = FlowState(user_id=user_id, query=query)
        pipeline = FlowPipeline(state)
        
        try:
            # 2. Intelligence Planning
            yield {"event": "activity", "data": "Architecting Neural Mission Strategy..."}
            state.intent = await self.planner.classify_task(state.query)
            state.plan = await self.planner.create_plan(state.query, state.intent)
            yield {"event": "metadata", "data": {"intent": state.intent, "mission_steps": len(state.plan), "request_id": str(state.start_time)}}
            
            # 3. Standardized Agent Dispatch
            yield {"event": "activity", "data": "Dispatching Sovereign Fleet..."}
            await self._execute_mission_fleet(state)
            
            # Log Mission Fleet Execution
            self._log_mission_execution(state)
            
            # 4. Neural Response Synthesis (Real streaming)
            yield {"event": "activity", "data": "Synthesizing Mission Intelligence..."}
            
            from backend.engines.chat.generation import SovereignGenerator
            generator = SovereignGenerator()
            
            context_mission = ""
            for s_id, res in state.engine_results.items():
                context_mission += f"\n[Step {s_id}] Result: {res.message[:1500]}"

            history = [{"role": "system", "content": f"Sovereign Context: {context_mission}"}]
            
            state.final_response = ""
            async for token in generator.stream_response(messages=history + [{"role": "user", "content": state.query}], lang=lang):
                state.final_response += token
                yield {"token": token}

            # 5. Global Telemetry Pulse & Memory Persistence
            state.latency_ms = (time.perf_counter() - state.start_time) * 1000
            yield {"event": "metadata", "data": {"latency_ms": state.latency_ms, "status": "completed"}}
            
            # 6. Automatic Memory Persistence (Background)
            asyncio.create_task(self._persist_mission_memory(state))

        except Exception as e:
            logger.error(f"Orchestration Anomaly: {e}", exc_info=True)
            yield {"event": "error", "data": f"Mission interrupted: {str(e)}"}

    async def _persist_mission_memory(self, state: FlowState):
        """Asynchronous memory consolidation and self-evolution for the Sovereign OS."""
        try:
            from backend.engines.memory.vault import MemoryVault
            from backend.engines.brain.learning_loop import LearningLoop
            
            # 1. Memory Persistence
            vault = MemoryVault(state.user_id)
            mock_embedding = [0.1] * 384 
            await vault.store(
                content=f"User asked: {state.query}\nLEVI responded: {state.final_response}",
                embedding=mock_embedding,
                metadata={"intent": state.intent, "latency": state.latency_ms}
            )
            
            # 2. Neural Telemetry Ingestion (Self-Evolution)
            evolver = LearningLoop()
            await evolver.ingest_telemetry(state)
            
            logger.info(f"[Orchestrator] Mission intelligence and telemetry persisted for {state.user_id}")
        except Exception as e:
            logger.error(f"Persistence/Learning failure: {e}")

    def _log_mission_execution(self, state: FlowState):
        """Standardized v7 Mission execution logging for global analytics."""
        mission_log = {
            "user_id": state.user_id,
            "query": state.query,
            "intent": state.intent,
            "steps": len(state.plan),
            "agents_used": [s["agent_name"] for s in state.plan],
            "results": {s_id: res.success for s_id, res in state.engine_results.items()},
            "timestamp": datetime.fromtimestamp(state.start_time).isoformat()
        }
        logger.info(f"[MissionLogger] Mission complete: {json.dumps(mission_log)}")

    async def _execute_mission_fleet(self, state: FlowState):
        """Dispatches the plan across the Sovereign registry."""
        executed = set()
        
        while len(executed) < len(state.plan):
            ready = [s for s in state.plan if s["step"] not in executed and (not s.get("depends_on") or s["depends_on"] in executed)]
            if not ready: break

            tasks = []
            for step in ready:
                # Use registry mapping
                agent_name = step.get("agent_name", step.get("action_key"))
                params = step.get("params", {}).copy()
                params["user_id"] = state.user_id
                
                # Context passing logic
                if step.get("depends_on"):
                    prev_res = state.engine_results.get(step["depends_on"])
                    params["input_context"] = prev_res.message if prev_res else ""

                tasks.append(self._dispatch_agent_step(step["step"], agent_name, params, state))
            
            if tasks: await asyncio.gather(*tasks)
            for s in ready: executed.add(s["step"])

    async def _dispatch_agent_step(self, step_id, name, params, state):
        """Unified dispatch to the hardened agent registry."""
        await AuditLogger.log_event(
            event_type="AGENT",
            action="Dispatch",
            user_id=state.user_id,
            resource_id=name,
            metadata={"step_id": step_id, "params_keys": list(params.keys())}
        )
        result = await AgentRegistry.dispatch(name, params)
        state.engine_results[step_id] = result
        
        await AuditLogger.log_event(
            event_type="AGENT",
            action="Result",
            user_id=state.user_id,
            resource_id=name,
            status="success" if result.success else "failed",
            metadata={"step_id": step_id, "error": result.error if not result.success else None}
        )

    async def synthesize_mission_results(self, state: FlowState, lang: str = "en") -> str:
        """Final synthesis mission via the DialogueArchitect."""
        if not state.engine_results:
            return SovereignI18n.get_prompt("error_fallback", lang)

        context_mission = ""
        for s_id, res in state.engine_results.items():
            context_mission += f"\n[Step {s_id}] Result: {res.message[:1500]}"

        # Engage the DialogueArchitect for final synthesis
        final_res = await AgentRegistry.dispatch("chat", {
            "input": state.query,
            "history": [{"role": "system", "content": f"Context: {context_mission}"}],
            "mood": "philosophical"
        })
        
        return final_res.message if final_res.success else final_res.error

# Global Orchestration Pulse
orchestrator = BrainOrchestrator()
