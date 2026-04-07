import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class EngineRegistry:
    """
    LeviBrain v8.12: Engine Registry (CORE HUB)
    Centrally manages deterministic engines for math, logic, and code.
    """

    def __init__(self):
        self.engines = {}
        
        # v13.1.0-Hardened-PROD: Default Cognitive & Logic Engines
        from backend.engines.reasoning.reasoning_engine import ReasoningEngine
        from backend.engines.deterministic_engine import DeterministicEngine
        
        self.register("Reasoning", ReasoningEngine())
        self.register("Deterministic", DeterministicEngine())
        logger.info("[EngineRegistry] Core v13.1.0-Hardened-PROD Logic Hub initialized.")

    def register(self, name: str, engine: Any):
        """Registers a new deterministic engine."""
        self.engines[name] = engine
        logger.info(f"[EngineRegistry] Registered engine: {name}")

    def get(self, name: str) -> Optional[Any]:
        """Retrieves an engine instance by name."""
        return self.engines.get(name)

    async def execute(self, engine_name: str, task_input: str) -> Dict[str, Any]:
        """
        Executes a registered engine deterministically.
        Supports falling back to tool calling for unregistered agents.
        """
        engine = self.get(engine_name)
        
        if not engine:
            # Bridging Logic: Fallback to call_tool for legacy agents
            logger.info(f"[EngineRegistry] Engine {engine_name} not registered. Falling back to call_tool.")
            from backend.core.tool_registry import call_tool
            from backend.orchestrator_types import ToolResult
            
            try:
                raw_res = await call_tool(engine_name, {"input": task_input})
                if isinstance(raw_res, dict):
                    return {
                        "success": raw_res.get("success", True),
                        "data": raw_res.get("data"),
                        "message": raw_res.get("message", ""),
                        "engine": engine_name
                    }
                elif isinstance(raw_res, ToolResult):
                    return {
                        "success": raw_res.success,
                        "data": raw_res.data,
                        "message": raw_res.message,
                        "engine": engine_name
                    }
                return {"success": True, "data": str(raw_res), "message": str(raw_res), "engine": engine_name}
            except Exception as e:
                logger.error(f"[EngineRegistry] Fallback failed for {engine_name}: {e}")
                raise Exception(f"Engine {engine_name} execution failed.")

        # Support both sync and async run methods
        logger.info(f"[EngineRegistry] Executing engine: {engine_name}")
        if hasattr(engine, "run"):
            import asyncio
            if asyncio.iscoroutinefunction(engine.run):
                return await engine.run(task_input)
            return engine.run(task_input)
        
        raise Exception(f"Engine {engine_name} has no 'run' method")
