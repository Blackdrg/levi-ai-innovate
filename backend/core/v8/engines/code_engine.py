import logging

logger = logging.getLogger(__name__)

class CodeEngine:
    """
    Code Execution Engine (v8.15)
    Executes Python logic directly for complex calculations and data processing.
    """

    def run(self, code: str):
        try:
            logger.info(f"[CodeEngine] Executing script: len={len(code)}")
            
            # Safe globals: Remove all builtins
            safe_globals = {"__builtins__": {}}
            local_env = {}

            # Execute code in a restricted environment
            exec(code, safe_globals, local_env)

            # Standardize output: return only user-defined local variables
            # Filter out internal variables if any
            result_data = {k: v for k, v in local_env.items() if not k.startswith('_')}

            return {
                "success": True,
                "data": result_data,
                "engine": "code",
                "message": f"Code execution successful. Variables: {list(result_data.keys())}"
            }
        except Exception as e:
            logger.error(f"[CodeEngine] Error: {e}")
            return {"success": False, "error": str(e), "engine": "code"}
