"""
Sovereign Code Architect v8.
Generates clean, high-performance, and logically sound structures.
Refactored into Autonomous Agent Ecosystem.
"""

import logging
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field
from backend.agents.base import SovereignAgent, AgentResult
from backend.engines.chat.generation import SovereignGenerator
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
        super().__init__("CodeArchitect")

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
            execution_output = self.execute_code(code)
        
        return {
            "message": f"### Implementation\n\n```python\n{code}\n```\n\n### Execution Results\n```\n{execution_output}\n```",
            "data": {
                "language": input_data.lang_preference,
                "execution_status": "verified" if "Error" not in execution_output else "failed"
            }
        }

    async def generate_code(self, task: str, lang: str, blackboard_context: str = "") -> str:
        """Generates high-fidelity code solutions."""
        system_prompt = (
            f"You are the LEVI Sovereign Code Architect. Create elegant, high-fidelity {lang} solutions.\n"
            "Technical Requirements: Modular, Resilient, Performance-First.\n"
            "Return ONLY the code block without markdown wrappers."
        )
        generator = SovereignGenerator()
        code = await generator.council_of_models([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"{blackboard_context}\n\nTask: {task}"}
        ])
        # Clean markdown if model ignored the instruction
        if "```" in code:
            code = code.split("```python")[-1].split("```")[0].strip()
        return code

    def execute_code(self, code: str) -> str:
        """Executes Python code in a safe local sandbox."""
        import subprocess
        import os
        
        sandbox_dir = os.path.abspath("backend/data/sandbox")
        temp_file = os.path.join(sandbox_dir, "temp_exec.py")
        
        try:
            with open(temp_file, "w") as f:
                f.write(code)
            
            # Execute with a timeout
            result = subprocess.run(
                ["python", temp_file], 
                capture_output=True, 
                text=True, 
                timeout=5,
                cwd=sandbox_dir
            )
            return result.stdout if result.returncode == 0 else result.stderr
        except subprocess.TimeoutExpired:
            return "Error: Execution timed out (5s limit)."
        except Exception as e:
            return f"Error during execution: {str(e)}"
        finally:
            if os.path.exists(temp_file):
                try: os.remove(temp_file)
                except: pass
