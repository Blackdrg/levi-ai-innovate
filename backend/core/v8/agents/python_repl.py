import logging
import sys
import io
import traceback
import asyncio
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from .base import BaseV8Agent, AgentResult

logger = logging.getLogger(__name__)

class PythonInput(BaseModel):
    code: str = Field(..., description="The Python code to execute")
    timeout: int = Field(default=5, description="Execution timeout in seconds")

class PythonReplAgentV8(BaseV8Agent[PythonInput]):
    """
    Sovereign Logic & Calculation Engine v8.7.
    Safely executes Python code in a restricted local environment.
    Integrated into the Swarm Orchestration logic for code verification.
    """
    
    def __init__(self):
        super().__init__("PythonREPLAgentV8")

    async def _execute_system(self, input_data: PythonInput, context: Dict[str, Any]) -> AgentResult:
        """
        Execution Protocol v8.7:
        1. Static Security Analysis.
        2. Restricted Global Sandbox.
        3. Parallel-safe execution.
        """
        code = input_data.code
        self.logger.info(f"[Python-V8] Executing logic mission: '{code[:40]}...'")
        
        # 1. Static Security Check
        disallowed = ["os", "subprocess", "sys", "eval", "exec", "open", "getattr", "setattr", "importlib", "shutil", "socket", "requests"]
        for d in disallowed:
            # Simple heuristic for safety
            if f"{d}." in code or f" {d}(" in code or f"({d}" in code:
                  return AgentResult(
                      success=False, 
                      error=f"Security Violation: '{d}' is forbidden in Sovereign Sandbox.",
                      message="Neural link blocked due to security integrity breach."
                  )

        # 2. Local Restricted Execution
        output_buffer = io.StringIO()
        old_stdout, old_stderr = sys.stdout, sys.stderr
        sys.stdout, sys.stderr = output_buffer, output_buffer

        # Restricted Globals (V8.8 Hardened)
        import math, json, datetime, random, statistics
        restricted_globals = {
            "__builtins__": {
                "print": print, "range": range, "len": len, "int": int, "float": float,
                "str": str, "list": list, "dict": dict, "set": set, "sum": sum,
                "min": min, "max": max, "abs": abs, "round": round, "map": map, "filter": filter,
                "any": any, "all": all, "enumerate": enumerate, "bool": bool, "zip": zip,
                "pow": pow, "divmod": divmod
            },
            "math": math,
            "json": json,
            "datetime": datetime,
            "random": random,
            "statistics": statistics
        }

        try:
            def _exec_logic():
                # Perform the execution in a dedicated scope
                exec(code, restricted_globals)
            
            # 3. Async Safe Threading
            await asyncio.wait_for(asyncio.to_thread(_exec_logic), timeout=input_data.timeout)
            
            output = output_buffer.getvalue()
            
            return AgentResult(
                success=True,
                message=output if output else "Logic pass completed with null output.",
                data={"output": output, "execution_success": True}
            )
            
        except asyncio.TimeoutError:
            return AgentResult(success=False, error=f"Mission timed out after {input_data.timeout}s.")
        except Exception as e:
            error_trace = traceback.format_exc()
            self.logger.warning(f"[Python-V8] Logic Mission failed: {e}")
            return AgentResult(
                success=False,
                error=f"Logic Anomaly: {str(e)}",
                data={"traceback": error_trace}
            )
        finally:
            sys.stdout, sys.stderr = old_stdout, old_stderr
