"""
backend/services/orchestrator/agents/python_repl_agent.py

Logical Verification Engine v1.0
Allows the LEVI-AI Brain to execute code in a basic sandboxed environment.
"""

import logging
import sys
import io
import traceback
from typing import Any, Dict
from pydantic import BaseModel, Field
from backend.utils.network import ai_service_breaker
from ..tool_base import BaseTool, StandardToolOutput

logger = logging.getLogger(__name__)

class PythonREPLInput(BaseModel):
    code: str = Field(..., description="The Python code to execute")
    timeout: int = Field(30, description="Max execution time in seconds")

class PythonREPLAgent(BaseTool[PythonREPLInput, StandardToolOutput]):
    """
    Calculation & Logic Engine.
    Uses the public Piston API for containerized execution (security hardening).
    Falls back to a restricted local exec() if the API is unreachable.
    """
    name = "python_repl_agent"
    description = "Calculation engine. Safely executes Python code for logical verification."
    input_schema = PythonREPLInput
    output_schema = StandardToolOutput

    async def _run(self, input_data: PythonREPLInput, context: Dict[str, Any]) -> Dict[str, Any]:
        request_id = context.get("request_id", "external")
        logger.info(f"[{request_id}] [PythonREPLAgent] Executing code: {input_data.code[:50]}...")
        
        # 1. Primary: Remote Containerized Sandbox (Piston API)
        try:
            from backend.utils.network import async_safe_request
            piston_url = "https://emkc.org/api/v2/piston/execute"
            
            payload = {
                "language": "python",
                "version": "3.10.0",
                "files": [{"name": "main.py", "content": input_data.code}],
                "run_timeout": min(input_data.timeout * 1000, 5000) # Max 5s for public API
            }
            
            resp = await async_safe_request("POST", piston_url, json=payload, request_id=request_id)
            data = resp.json()
            
            run_result = data.get("run", {})
            success = run_result.get("code") == 0
            output = run_result.get("output", "")
            stderr = run_result.get("stderr", "")
            
            logger.info(f"[{request_id}] [Piston] Execution successful: {success}")
            
            return {
                "success": success,
                "message": output if success else f"Execution failed: {stderr or output}",
                "data": {"output": output, "stderr": stderr, "backend": "piston"},
                "agent": self.name
            }

        except Exception as e:
            logger.warning(f"[{request_id}] Piston API failed or timed out: {e}. Falling back to local restricted exec.")
            # 2. Fallback: Restricted Local Execution
            result = await ai_service_breaker.async_call(self._execute_local_fallback, input_data.code)
            return result

    async def _execute_local_fallback(self, code: str) -> Dict[str, Any]:
        """
        Restricted local exec() as a safety fallback.
        """
        output_buffer = io.StringIO()
        old_stdout, old_stderr = sys.stdout, sys.stderr
        sys.stdout, sys.stderr = output_buffer, output_buffer

        restricted_globals = {
            "__builtins__": {
                "print": print, "range": range, "len": len, "int": int, "float": float,
                "str": str, "list": list, "dict": dict, "set": set, "sum": sum,
                "min": min, "max": max, "abs": abs, "round": round
            },
            "math": __import__("math"),
            "json": __import__("json"),
            "datetime": __import__("datetime")
        }

        success, error_msg = True, None
        try:
            # Basic static analysis check
            disallowed = ["os.", "subprocess.", "sys.", "eval", "exec", "open", "getattr", "setattr"]
            for d in disallowed:
                if d in code:
                    raise SecurityError(f"Use of disallowed keyword/module: {d}")

            exec(code, restricted_globals)
            output = output_buffer.getvalue()
        except Exception:
            success, error_msg = False, traceback.format_exc()
            output = output_buffer.getvalue()
        finally:
            sys.stdout, sys.stderr = old_stdout, old_stderr

        return {
            "success": success,
            "message": output if success else f"Local execution failed: {error_msg}",
            "data": {"output": output, "error": error_msg, "backend": "local_fallback"},
            "agent": self.name
        }

class SecurityError(Exception):
    pass
