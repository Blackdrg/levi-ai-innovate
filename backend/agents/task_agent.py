"""
Sovereign Task Architect v8.
Decomposes complex goals into recursive sub-tasks and delegates to specialized agents.
Refactored into Autonomous Agent Ecosystem.
"""

import logging
import json
from typing import Dict, Any
from pydantic import BaseModel, Field
from backend.agents.base import SovereignAgent, AgentResult
from backend.engines.chat.generation import SovereignGenerator

logger = logging.getLogger(__name__)

class TaskInput(BaseModel):
    input: str = Field(..., description="The complex goal to decompose")
    user_id: str = "guest"

class TaskAgent(SovereignAgent[TaskInput, AgentResult]):
    """
    Sovereign Task Architect.
    Decomposes complex user goals into logical execution steps and specialized delegation.
    """
    
    def __init__(self):
        super().__init__("TaskArchitect")

    async def _run(self, input_data: TaskInput, lang: str = "en", **kwargs) -> Dict[str, Any]:
        """
        Planning Protocol v8:
        1. Contextual Goal Decomposition.
        2. Sequence Mapping.
        3. Council-based Strategy Synthesis.
        """
        goal = input_data.input
        self.logger.info(f"Architecting Mission Strategy: {goal[:50]}")
        
        system_prompt = (
            "You are the LEVI Sovereign Task Architect. Decompose complex user goals into logical execution steps.\n"
            "Execution Requirements:\n"
            "- Strategy: Unified, high-fidelity approach.\n"
            "- Delegation: Optimize for agent specialization (Research, Studio, PythonREPL, etc.).\n"
            "Output ONLY valid JSON:\n"
            "{\n"
            "  \"strategy\": \"High-level approach summary\",\n"
            "  \"steps\": [\n"
            "    {\"step\": 1, \"task\": \"Task description\", \"agent\": \"AgentName\", \"reason\": \"Why this agent?\"}\n"
            "  ]\n"
            "}"
        )
        
        generator = SovereignGenerator()
        
        # Engage the Council for complex strategy synthesis
        raw_json = await generator.council_of_models([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Decompose following mission: {goal}"}
        ])
        
        try:
            content = raw_json.strip()
            if "```json" in content: content = content.split("```json")[1].split("```")[0]
            elif "```" in content: content = content.split("```")[1].split("```")[0]
            
            data = json.loads(content)
            strategy = data.get("strategy", "Unknown Strategy")
            steps = data.get("steps", [])
            
            # Formulate Sovereign Mission Plan
            step_text = "\n".join([f"{s['step']}. **{s['task']}** (Agent: {s['agent']})" for s in steps])
            message = (
                f"### [Sovereign Mission Strategy]\n\n"
                f"**Strategy**: {strategy}\n\n"
                f"**Execution Vector**:\n{step_text}\n"
            )

            return {
                "message": message,
                "data": {
                    "strategy": strategy,
                    "steps": steps,
                    "mission_depth": len(steps)
                }
            }
            
        except Exception as e:
            self.logger.error(f"Task Architect Strategy Failure: {e}")
            return {
                "message": "Strategy synthesis interrupted by data anomaly.",
                "success": False
            }
