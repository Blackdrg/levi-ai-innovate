import logging
from typing import Any, Dict
from pydantic import BaseModel, Field
from backend.core.agent_base import SovereignAgent, AgentResult
from backend.engines.chat.generation import SovereignGenerator

logger = logging.getLogger(__name__)

class CodeInput(BaseModel):
    input: str = Field(..., description="The coding task or architectural query")
    user_id: str = "guest"
    lang_preference: str = "Python"

class CodeAgent(SovereignAgent[CodeInput, AgentResult]):
    """
    Sovereign Code Architect (CodeArchitect).
    Generates clean, high-performance, and logically sound structures.
    """
    
    def __init__(self):
        super().__init__("CodeArchitect")

    async def _run(self, input_data: CodeInput, lang: str = "en", **kwargs) -> Dict[str, Any]:
        """
        Co-Creation Protocol v7:
        1. Architectural Intent Analysis.
        2. Council-based Implementation (High-Fidelity).
        """
        task = input_data.input
        self.logger.info(f"Architecting Code Mission: {task[:50]}")
        
        system_prompt = (
            "You are the LEVI Sovereign Code Architect. Create elegant, high-fidelity code solutions.\n"
            "Technical Requirements:\n"
            "- Architecture: Modular, Resilient, Performance-First.\n"
            "- Compliance: Standardized Security & Typings.\n"
            "- Implementation: {0}\n"
        ).format(input_data.lang_preference)
        
        generator = SovereignGenerator()
        
        # Engage the Council for complex architecture
        final_output = await generator.council_of_models([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Implement the following mission: {task}"}
        ])
        
        return {
            "message": final_output,
            "data": {
                "language": input_data.lang_preference,
                "complexity": "high" if len(final_output) > 2500 else "optimized"
            }
        }
