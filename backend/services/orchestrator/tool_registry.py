from typing import Dict, Any, Callable, Awaitable
import logging

logger = logging.getLogger(__name__)

# Type definition for atomic tool calls
ToolFunc = Callable[[Dict[str, Any]], Awaitable[Any]]

TOOLS: Dict[str, ToolFunc] = {}

def register_tool(name: str):
    def decorator(func: ToolFunc):
        TOOLS[name] = func
        return func
    return decorator

async def call_tool(name: str, params: Dict[str, Any]) -> Any:
    if name not in TOOLS:
        logger.error(f"Tool {name} not found in registry.")
        return {"error": f"Tool {name} not found"}
    
    logger.info(f"Calling tool: {name}")
    try:
        return await TOOLS[name](params)
    except Exception as e:
        logger.exception(f"Error executing tool {name}: {e}")
        return {"error": str(e)}

# --- Placeholder Tools ---

@register_tool("image_gen")
async def tool_image_gen(params: Dict[str, Any]) -> Any:
    return {"status": "success", "action": "trigger_image_generation", "params": params}

@register_tool("db_write")
async def tool_db_write(params: Dict[str, Any]) -> Any:
    # This would call firestore_db/redis_client
    return {"status": "success", "action": "database_write", "params": params}

@register_tool("search_api")
async def tool_search_api(params: Dict[str, Any]) -> Any:
    return {"status": "success", "results": [{"title": "AI Trends", "snippet": "Future is bright."}]}
