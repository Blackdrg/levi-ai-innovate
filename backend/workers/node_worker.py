# backend/workers/node_worker.py
import sys
import asyncio
import json
import os
import logging
import time
from typing import Dict, Any

# Ensure we can import from backend
sys.path.append(os.getcwd())

from backend.utils.event_bus import sovereign_event_bus
from backend.core.agent_registry import AgentRegistry
from backend.core.tool_registry import call_tool
from backend.core.orchestrator_types import ToolResult, AgentState

# Configure logging to stdout for HAL-0 capture
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger("node_worker")

async def execute_task(mission_id: str, node_id: str, agent_name: str, params_json: str, context_json: str):
    """
    Sovereign v17.0: HAL-0 Isolated Node Worker.
    Executes a single agent node in a dedicated process.
    """
    start_time = time.time()
    logger.info(f"🚀 [NodeWorker] Starting Task: {node_id} (Agent: {agent_name}) for Mission: {mission_id}")
    
    try:
        params = json.loads(params_json)
        context = json.loads(context_json)
        
        # 1. Dispatch to local tool/agent
        # We use call_tool which is the standard entry point for local execution
        raw_res = await call_tool(agent_name, params, context)
        
        # 2. Convert to ToolResult structure
        if isinstance(raw_res, dict):
            result = ToolResult(**raw_res)
        else:
            result = raw_res
            
        result.agent = agent_name
        result.latency_ms = int((time.time() - start_time) * 1000)
        
        logger.info(f"✅ [NodeWorker] Task {node_id} success in {result.latency_ms}ms")
        
    except Exception as e:
        logger.error(f"💥 [NodeWorker] Task {node_id} failure: {e}")
        result = ToolResult(
            success=False,
            error=str(e),
            agent=agent_name,
            state=AgentState.FAILED,
            latency_ms=int((time.time() - start_time) * 1000)
        )

    # 3. Publish Result to EventBus (Phase 2.3)
    # The Orchestrator is listening for results on "agent.results" stream
    await sovereign_event_bus.emit_event(
        topic="agent.results",
        event_type="NODE_COMPLETED",
        payload=result.model_dump() if hasattr(result, "model_dump") else result.dict(),
        mission_id=mission_id,
        source=f"node_worker:{node_id}"
    )
    
    logger.info(f"🏁 [NodeWorker] Result emitted for {node_id}. Exiting.")

if __name__ == "__main__":
    if len(sys.argv) < 6:
        print("Usage: python node_worker.py <mission_id> <node_id> <agent_name> <params_json> <context_json>")
        sys.exit(1)
        
    m_id = sys.argv[1]
    n_id = sys.argv[2]
    a_name = sys.argv[3]
    p_json = sys.argv[4]
    c_json = sys.argv[5]
    
    asyncio.run(execute_task(m_id, n_id, a_name, p_json, c_json))
