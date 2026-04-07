"""
Sovereign Calculation & Logic Engine v8.
Safely executes Python code in a restricted local environment.
Refactored into Autonomous Agent Ecosystem.
"""

import logging
import asyncio
from typing import Any, Dict
from pydantic import BaseModel, Field
from backend.agents.base import SovereignAgent, AgentResult

logger = logging.getLogger(__name__)

class PythonInput(BaseModel):
    code: str = Field(..., description="The Python code to execute")
    timeout: int = 5

class PythonReplAgent(SovereignAgent[PythonInput, AgentResult]):
    """
    Sovereign Python REPL.
    Executes restricted Python code for calculation, logic, and data analysis missions.
    """
    
    def __init__(self):
        super().__init__("PythonREPL")

    async def _run(self, input_data: PythonInput, lang: str = "en", **kwargs) -> Dict[str, Any]:
        """
        Execution Protocol v13 (Hardened Docker Sandbox):
        1. Multi-layer Isolation.
        2. Strict Resource Limiting.
        3. No Network Access.
        """
        from backend.utils.sandbox import DockerSandbox
        
        code = input_data.code
        self.logger.info(f"Executing Isolated Logic Mission: {code[:50]}...")
        
        # 1. Execute in Docker
        result = await asyncio.to_thread(DockerSandbox.execute, code)
        
        return {
            "success": result["success"],
            "message": result["message"],
            "data": result.get("data", {})
        }
