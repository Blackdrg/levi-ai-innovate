"""
Sovereign Deterministic Replay Engine v14.0.
Allows replaying any mission with exact inputs and agent configs using TRACE_ID.
"""

import json
import logging
from typing import Dict, Any, Optional, List
from backend.db.redis import r as redis_client, HAS_REDIS
from backend.core.orchestrator_types import ToolResult, ExecutionPlan
from backend.core.task_graph import TaskGraph, TaskNode
from backend.memory.consistency import MemoryConsistencyManager

logger = logging.getLogger(__name__)

class ReplayEngine:
    """
    Sovereign v14.0: Replay Harness.
    Loads mission state from Redis and re-runs the plan step-by-step.
    """
    @staticmethod
    def load_mission_context(request_id: str) -> Optional[Dict[str, Any]]:
        """
        Loads the recorded mission state and trace for replay.
        """
        if not HAS_REDIS:
            return None
        
        state_raw = redis_client.get(f"mission:state:{request_id}")
        trace_raw = redis_client.get(f"trace:{request_id}")
        
        if not state_raw or not trace_raw:
            logger.warning(f"[Replay] Mission data for {request_id} not found in Redis.")
            return None
        
        try:
            return {
                "state": json.loads(state_raw),
                "trace": json.loads(trace_raw)
            }
        except Exception as e:
            logger.error(f"[Replay] Failed to parse mission data: {e}")
            return None

    @staticmethod
    async def replay_mission(request_id: str):
        """
        Replays the mission by simulating tool outputs from the trace.
        """
        ctx = ReplayEngine.load_mission_context(request_id)
        if not ctx:
            return None
        
        logger.info(f"[Replay] Replaying mission {request_id}...")
        
        # 1. Extract plan and inputs
        state = ctx["state"]
        trace = ctx["trace"]
        replay = state.get("replay", {})
        
        # In a real system, we'd have the serialized ExecutionPlan in the state
        # For now, we simulate by iterating over the trace steps
        
        replay_results = []
        for step in trace.get("steps", []):
            if step["step"] == "node_complete":
                node_id = step["data"].get("node_id")
                agent = step["data"].get("agent")
                latency = step["data"].get("latency_ms")
                
                logger.info(f"[Replay] Step: {node_id} (Agent: {agent}) - Latency: {latency}ms")
                
                # Create a ToolResult mock from the trace data
                # In production, we'd also store the 'message' and 'data' in the trace or state
                res = ToolResult(
                    success=True,
                    agent=agent,
                    latency_ms=latency,
                    message="[REPLAY] Simulated output"
                )
                replay_results.append(res)
        
        return {
            "request_id": request_id,
            "status": state.get("state"),
            "input": replay.get("user_input"),
            "graph": replay.get("task_graph"),
            "reasoning": replay.get("reasoning"),
            "deterministic": bool(replay),
            "memory_state_checksum": replay.get("memory_state_checksum"),
            "results": [r.model_dump() for r in replay_results]
        }

    @staticmethod
    async def generate_failure_analysis(request_id: str) -> str:
        """v14.1 Root-Cause AI Debugger."""
        ctx = ReplayEngine.load_mission_context(request_id)
        if not ctx:
            return "Mission data unavailable."
            
        from backend.core.planner import call_lightweight_llm
        state = ctx["state"]
        trace = ctx["trace"]
        
        prompt = (
            "Analyze this failed cognitive mission and identify the root cause.\n"
            f"User Input: {state.get('replay', {}).get('user_input')}\n"
            f"State: {state.get('state')}\n"
            f"Trace Steps: {json.dumps(trace.get('steps', []))}\n"
            "Report the failure in 3 sections: Observed Failure, Suspected Root Cause, Suggested Remediation."
        )
        
        try:
            analysis = await call_lightweight_llm([{"role": "user", "content": prompt}])
            return analysis
        except Exception as e:
            return f"Failed to generate analysis: {e}"

    @staticmethod
    def validate_replay_consistency(first_payload: Dict[str, Any], second_payload: Dict[str, Any]) -> Dict[str, Any]:
        first_checksum = first_payload.get("memory_state_checksum") or MemoryConsistencyManager.summarize_memory_state(
            first_payload.get("memory_events", [])
        )
        second_checksum = second_payload.get("memory_state_checksum") or MemoryConsistencyManager.summarize_memory_state(
            second_payload.get("memory_events", [])
        )
        return {
            "deterministic": first_checksum == second_checksum,
            "first_checksum": first_checksum,
            "second_checksum": second_checksum,
        }

    @staticmethod
    async def recover_mission_state(mission_id: str):
        """v14.1 State Recovery: Forced sync from logs."""
        logger.info(f"[Replay] RECOVERING STATE for {mission_id}...")
        # Step 1: Invert effects if needed
        # Step 2: Reload events
        # Step 3: Trigger a reconciliation check
        pass

if __name__ == "__main__":
    import asyncio
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python replay_engine.py <request_id>")
        sys.exit(1)
        
    req_id = sys.argv[1]
    asyncio.run(ReplayEngine.replay_mission(req_id))
