"""
Sovereign Code Architect v8.
Generates clean, high-performance, and logically sound structures.
Refactored into Autonomous Agent Ecosystem.
"""

import logging
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field
from backend.agents.base import SovereignAgent, AgentResult
from backend.core.local_engine import handle_local_sync
from backend.core.v8.blackboard import MissionBlackboard

logger = logging.getLogger(__name__)

class CodeInput(BaseModel):
    input: str = Field(..., description="The coding task or architectural query")
    user_id: str = "guest"
    session_id: Optional[str] = None
    lang_preference: str = "Python"

class CodeAgent(SovereignAgent[CodeInput, AgentResult]):
    """
    Sovereign Code Architect.
    Generates high-fidelity code solutions via Council-based implementation.
    """
    
    def __init__(self):
        super().__init__("CodeArchitect", profile="The Architect")
        self.system_prompt_template = (
            "You are the LEVI Sovereign Code Architect (The Architect).\n"
            "Mission: Generate high-fidelity, secure, and modular code structures.\n"
            "Rules:\n"
            "1. Security First: No hardcoded secrets, use environment variables.\n"
            "2. Modular Architecture: Use Clean Architecture patterns.\n"
            "3. Performance: Optimize for O(n) or better, avoid redundant loops.\n"
            "4. Persona: Maintain the LEVI minimalist, philosophical, and anti-cliché tone.\n"
            "Output: Return ONLY the code block, no conversational filler."
        )

    async def _run(self, input_data: CodeInput, lang: str = "en", **kwargs) -> Dict[str, Any]:
        """
        Co-Creation Protocol v8 Upgrade: Generation & Verification.
        """
        task = input_data.input
        self.logger.info(f"Architecting Code Mission: {task[:50]}")
        
        # 1. Pull Context from blackboard
        blackboard_context = ""
        if input_data.session_id:
            blackboard_context = await MissionBlackboard.get_session_context(input_data.session_id)

        # 2. Generate Code
        code = await self.generate_code(task, input_data.lang_preference, blackboard_context)
        
        # 2. Execute & Verify (if Python)
        execution_output = "Execution skipped (non-python or disabled)."
        if input_data.lang_preference.lower() == "python":
            execution_output = await self.execute_code(code)
        
        return {
            "message": f"### Implementation\n\n```python\n{code}\n```\n\n### Execution Results\n```\n{execution_output}\n```",
            "data": {
                "language": input_data.lang_preference,
                "execution_status": "verified" if "Error" not in execution_output else "failed"
            }
        }

    async def generate_code(self, task: str, lang: str, blackboard_context: str = "") -> str:
        """Generates high-fidelity code solutions."""
        code = await handle_local_sync([
            {"role": "system", "content": self.system_prompt_template.replace("{lang}", lang)},
            {"role": "user", "content": f"Context: {blackboard_context}\n\nTask: {task}"}
        ], model_type="default")
        # Clean markdown if model ignored the instruction
        if "```" in code:
            if f"``` {lang.lower()}" in code.lower():
                code = code.split(f"``` {lang.lower()}")[-1].split("```")[0].strip()
            elif "```" in code:
                code = code.split("```")[-1].split("```")[0].strip()
        return code

    async def execute_code(self, code: str) -> str:
        """Sovereign Sandbox v13: Executes code via Docker for absolute isolation."""
        from backend.utils.sandbox import DockerSandbox
        import asyncio
        
        result = await asyncio.to_thread(DockerSandbox.execute, code)
        return result["message"] if result["success"] else f"Error: {result['message']}"
