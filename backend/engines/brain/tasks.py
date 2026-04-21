import logging
import asyncio
from backend.celery_app import celery_app
from backend.core.agent_registry import AgentRegistry
from backend.redis_client import cache

logger = logging.getLogger(__name__)

@celery_app.task(name="backend.engines.brain.tasks.run_agent_task", bind=True, max_retries=3)
def run_agent_task(self, payload: dict):
    """
    Distributed Agent Task.
    Each agent execution runs as a worker task.
    """
    mission_id = payload.get("mission_id")
    agent_name = payload.get("agent", "COGNITION").lower()
    input_data = payload.get("input")
    
    logger.info(f"🤖 [Worker] Running agent {agent_name} for mission {mission_id}")
    
    # 1. Update status in Redis
    cache.set(f"task:{self.request.id}:status", "executing", ex=600)
    
    # 2. Run Agent
    # Since Celery workers usually run in a sync loop, we use a loop to run the async agent dispatch
    async def _dispatch():
        try:
            from backend.core.agent_registry import AgentRegistry
            from backend.agents.base import AgentResult
            
            agent_cap = AgentRegistry.get_agent(agent_name)
            if not agent_cap:
                # Fallback to local sync if agent not found in registry
                from backend.core.local_engine import handle_local_sync
                logger.warning(f"Agent {agent_name} not found in registry, using fallback.")
                result = await handle_local_sync([
                    {"role": "system", "content": f"You are the {agent_name} agent."},
                    {"role": "user", "content": input_data}
                ])
                return {"status": "completed", "output": result}
            
            from backend.agents.cognition import CognitionAgent, CognitionInput
            from backend.agents.sentinel import SentinelAgent, SentinelInput
            from backend.agents.memory_agent import MemoryAgent, MemoryInput # LIBRARIAN
            from backend.agents.task_agent import TaskAgent, TaskInput # EXECUTOR
            
            agent_map = {
                "cognition": (CognitionAgent, CognitionInput),
                "sentinel": (SentinelAgent, SentinelInput),
                "librarian": (MemoryAgent, MemoryInput),
                "executor": (TaskAgent, TaskInput),
                # Aliases for MAS
                "researcher": (CognitionAgent, CognitionInput),
                "research": (CognitionAgent, CognitionInput),
                "writer": (CognitionAgent, CognitionInput),
                "critic": (SentinelAgent, SentinelInput),
                "auditor": (SentinelAgent, SentinelInput),
                "memory": (MemoryAgent, MemoryInput),
                "chat": (CognitionAgent, CognitionInput)
            }

            
            mapping = agent_map.get(agent_name.lower())
            if not mapping:
                from backend.core.local_engine import handle_local_sync
                result = await handle_local_sync([
                    {"role": "system", "content": f"You are the {agent_name} agent."},
                    {"role": "user", "content": input_data}
                ])
                return {"status": "completed", "output": result}

            agent_cls, input_cls = mapping
            agent_instance = agent_cls()
            
            try:
                # Prepare input data with user/session context if available
                input_kwargs = {"input": input_data}
                if hasattr(input_cls, "user_id"):
                    input_kwargs["user_id"] = payload.get("user_id", "system")
                if hasattr(input_cls, "session_id"):
                    input_kwargs["session_id"] = payload.get("session_id", mission_id or "default")
                
                validated_input = input_cls(**input_kwargs)
                res = await agent_instance.execute(validated_input)
                
                return {
                    "status": "completed" if res.success else "failed",
                    "output": res.message,
                    "error": res.error,
                    "agent": agent_name
                }
            except Exception as e:
                logger.error(f"Error executing agent {agent_name}: {e}")
                return {"status": "failed", "error": str(e)}


        except Exception as e:
            logger.error(f"Agent execution failed: {e}", exc_info=True)
            return {"status": "failed", "error": str(e)}


    loop = asyncio.get_event_loop()
    result = loop.run_until_complete(_dispatch())
    
    # 3. Store result in Redis
    cache.set(f"task:{self.request.id}:result", str(result), ex=600)
    cache.set(f"task:{self.request.id}:status", result["status"], ex=600)
    
    return result
