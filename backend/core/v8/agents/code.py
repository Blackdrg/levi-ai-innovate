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

class CodeData(BaseModel):
    task: str
    language: str
    architectural_spec: str
    implementation_logic: str
    test_suite: str
    complexity_evaluation: str = "standard"

class CodeAgentV8(BaseV8Agent[CodeInput]):
    """
    LeviBrain v8: Code Intelligence System
    Solution Architect + Logic Mapper
    """

    def __init__(self):
        super().__init__("CodeAgentV8")
        self.generator = SovereignGenerator()

    async def _execute_system(self, input_data: CodeInput, context: Dict[str, Any]) -> AgentResult[CodeData]:
        task = input_data.input
        self.logger.info(f"[Code-V8] starting structured system operation for: {task[:50]}")

        # 1. Solution Architect: Produce core logic
        solution = await self._architect_solution(task, input_data.language)
        
        # 2. Logic Mapper: Produce technical specs and structure
        specs = await self._generate_specs(task, solution, input_data.language)
        
        # 3. Tester: Produce verification logic / tests
        tests = await self._generate_tests(solution, input_data.language)
        
        return AgentResult(
            success=True,
            message=f"Architectural logic for '{task[:30]}...' finalized.",
            data=CodeData(
                task=task,
                language=input_data.language,
                architectural_spec=specs,
                implementation_logic=solution,
                test_suite=tests
            )
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

    async def _generate_specs(self, task: str, solution: str, language: str) -> str:
        prompt = (
            f"Task: {task}\nImplementation:\n{solution}\n\n"
            f"Produce a detailed technical specification for this {language} implementation."
        )
        return await self.generator.council_of_models([
            {"role": "system", "content": "You are the LEVI Technical Architect."},
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

