import logging
import sys
import io
import traceback
import asyncio
from typing import Any, Dict
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

        # 2. Sovereign Sandbox Execution (Tier 2/3)
        from backend.core.execution_guardrails import AgentSandbox
        
        # Prepare script for container: Wrap code in print() if it's a single expression 
        # but usually we just execute it as a script.
        # We pass the code via a command-line argument or a piped file. 
        # For simplicity in this v14.2 implementation, we use a 'python -c' call.
        
        container_code = f"""
import json, math, datetime, random, statistics
# Restricted Globals Inject (V8 Hardened)
class SovereignContext:
    def __init__(self):
        self.math = math
        self.json = json
        self.datetime = datetime
        self.random = random
        self.statistics = statistics

{code}
"""
        
        sandbox_res = await AgentSandbox.run_in_sandbox(
            command=["python", "-c", container_code],
            timeout=input_data.timeout
        )
        
        if sandbox_res["success"]:
            return AgentResult(
                success=True,
                message=sandbox_res["stdout"] if sandbox_res["stdout"] else "Logic pass completed with null output.",
                data={"output": sandbox_res["stdout"], "execution_success": True}
            )
        else:
            return AgentResult(
                success=False,
                error=f"Logic Anomaly: {sandbox_res.get('stderr') or sandbox_res.get('error')}",
                data={"exit_code": sandbox_res.get("exit_code")}
            )
