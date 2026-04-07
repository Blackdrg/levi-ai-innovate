import logging
import sys
import io
import traceback
import asyncio
from typing import Any, Dict
from pydantic import BaseModel, Field
from backend.core.agent_base import SovereignAgent, AgentResult

logger = logging.getLogger(__name__)

class PythonInput(BaseModel):
    code: str = Field(..., description="The Python code to execute")
    timeout: int = 5

class PythonReplAgent(SovereignAgent[PythonInput, AgentResult]):
    """
    Sovereign Calculation & Logic Engine (PythonREPL).
    Safely executes Python code in a restricted local environment.
    """
    
    def __init__(self):
        super().__init__("PythonREPL")

    async def _run(self, input_data: PythonInput, lang: str = "en", **kwargs) -> Dict[str, Any]:
        """
        Execution Protocol v7:
        1. Static Analysis: Prompt injection & exploit detection.
        2. Sandbox Setup: Restricted globals/builtins.
        3. Execution: Async with timeout.
        """
        code = input_data.code
        self.logger.info(f"Executing Logic Mission: {code[:50]}...")
        
        # 1. Static Security Check (Hardened for v7)
        disallowed = ["os", "subprocess", "sys", "eval", "exec", "open", "getattr", "setattr", "importlib", "shutil", "socket", "requests"]
        for d in disallowed:
            if f"{d}." in code or f" {d}(" in code or f"({d}" in code:
                  return {"success": False, "message": f"Security Violation: '{d}' is forbidden in Sovereign Sandbox."}

        # 2. Local Restricted Execution
        output_buffer = io.StringIO()
        old_stdout, old_stderr = sys.stdout, sys.stderr
        sys.stdout, sys.stderr = output_buffer, output_buffer

        # Restricted Globals for Global Readiness
        restricted_globals = {
            "__builtins__": {
                "print": print, "range": range, "len": len, "int": int, "float": float,
                "str": str, "list": list, "dict": dict, "set": set, "sum": sum,
                "min": min, "max": max, "abs": abs, "round": round, "map": map, "filter": filter,
                "any": any, "all": all, "enumerate": enumerate, "bool": bool, "zip": zip
            },
            "math": __import__("math"),
            "json": __import__("json"),
            "datetime": __import__("datetime"),
            "random": __import__("random"),
            "statistics": __import__("statistics")
        }

        try:
            # We use a thread to prevent blocking the event loop
            def _exec():
                exec(code, restricted_globals)
            
            await asyncio.wait_for(asyncio.to_thread(_exec), timeout=input_data.timeout)
            output = output_buffer.getvalue()
            
            return {
                "success": True,
                "message": output if output else "Operation completed with null output.",
                "data": {"output": output}
            }
            
        except asyncio.TimeoutError:
            return {"success": False, "message": f"Mission failed: Execution timed out after {input_data.timeout}s."}
        except Exception as e:
            error_trace = traceback.format_exc()
            self.logger.warning(f"Python Mission Failed: {e}")
            return {
                "success": False,
                "message": f"Logic Anomaly: {str(e)}",
                "data": {"traceback": error_trace}
            }
        finally:
            sys.stdout, sys.stderr = old_stdout, old_stderr
