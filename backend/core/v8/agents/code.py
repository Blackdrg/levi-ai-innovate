import logging
import asyncio
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from .base import BaseV8Agent, AgentResult
from backend.engines.chat.generation import SovereignGenerator

logger = logging.getLogger(__name__)

class CodeInput(BaseModel):
    input: str = Field(..., description="Coding task or architectural query")
    language: str = "Python"

class CodeAgentV8(BaseV8Agent[CodeInput]):
    """
    LeviBrain v8: Code Intelligence System
    Solution Architect + Tester + Refiner
    """

    def __init__(self):
        super().__init__("CodeAgentV8")
        self.generator = SovereignGenerator()

    async def _execute_system(self, input_data: CodeInput, context: Dict[str, Any]) -> AgentResult:
        task = input_data.input
        self.logger.info(f"[Code-V8] starting system operation for: {task[:50]}")

        # 1. Solution Architect: Produce core logic
        solution = await self._architect_solution(task, input_data.language)
        
        # 2. Tester: Produce verification logic / tests
        tests = await self._generate_tests(solution, input_data.language)
        
        # 3. Refiner: Final synthesis
        final_code = await self._refine_code(solution, tests)
        
        return AgentResult(
            success=True,
            message=final_code,
            data={
                "has_tests": True,
                "language": input_data.language,
                "components": ["Architect", "Tester", "Refiner"]
            }
        )

    async def _architect_solution(self, task: str, language: str) -> str:
        prompt = (
            f"Task: {task}\nLanguage: {language}\n\n"
            "Produce an elegant, high-performance implementation. Focus on modularity and security."
        )
        return await self.generator.council_of_models([
            {"role": "system", "content": "You are the LEVI Code Architect."},
            {"role": "user", "content": prompt}
        ])

    async def _generate_tests(self, code: str, language: str) -> str:
        prompt = (
            f"Code:\n{code}\n\n"
            f"Generate a robust unit test suite for this implementation in {language}."
        )
        return await self.generator.council_of_models([
            {"role": "system", "content": "You are the LEVI Test Engineer."},
            {"role": "user", "content": prompt}
        ])

    async def _refine_code(self, solution: str, tests: str) -> str:
        prompt = (
            f"Solution:\n{solution}\n\n"
            f"Tests:\n{tests}\n\n"
            "Review the solution and tests. Produce a final integrated code block including both, optimized for production."
        )
        return await self.generator.council_of_models([
            {"role": "system", "content": "You are the LEVI Code Refiner."},
            {"role": "user", "content": prompt}
        ])
