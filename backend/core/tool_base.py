"""
backend/services/orchestrator/tool_base.py

New foundation for a hardened, deterministic tool system.
Enforces strict Pydantic schemas for all tool inputs and outputs.
Includes built-in retries, timeouts, and structured error reporting.
"""

import asyncio
import logging
import time
from typing import Any, Dict, Generic, Optional, Type, TypeVar
from pydantic import BaseModel, Field, ValidationError

logger = logging.getLogger(__name__)

# Type variables for Pydantic models
I = TypeVar("I", bound=BaseModel)
O = TypeVar("O", bound=BaseModel)

class ToolError(Exception):
    """Base exception for tool-specific failures."""
    def __init__(self, message: str, retryable: bool = False, agent: str = "unknown"):
        super().__init__(message)
        self.message = message
        self.retryable = retryable
        self.agent = agent

class BaseTool(Generic[I, O]):
    """
    Base class for all LEVI tools/agents.
    Ensures input/output contracts and resilient execution.
    """
    
    name: str = "base_tool"
    description: str = "Base tool description"
    input_schema: Type[I] = BaseModel
    output_schema: Type[O] = BaseModel
    
    max_retries: int = 2
    timeout_sec: float = 30.0

    async def execute(self, params: Dict[str, Any], context: Dict[str, Any] = None) -> O:
        """
        Primary execution wrapper with validation, retry, and timeout.
        """
        context = context or {}
        start_time = time.time()
        last_error = None
        
        # 1. Input Validation
        try:
            validated_input = self.input_schema(**params)
        except ValidationError as e:
            logger.error(f"Tool '{self.name}' input validation failed: {e}")
            raise ToolError(f"Invalid input: {str(e)}", retryable=False, agent=self.name)

        # 2. Resilient Execution Loop
        for attempt in range(self.max_retries + 1):
            try:
                # Wrap core logic with timeout
                result_data = await asyncio.wait_for(
                    self._run(validated_input, context), 
                    timeout=self.timeout_sec
                )
                
                # 3. Output Validation
                try:
                    if isinstance(result_data, self.output_schema):
                        validated_output = result_data
                    else:
                        validated_output = self.output_schema(**result_data)
                    
                    return validated_output
                except ValidationError as e:
                    logger.error(f"Tool '{self.name}' output validation failed: {e}")
                    raise ToolError(f"Internal schema violation: {str(e)}", retryable=False, agent=self.name)
            
            except asyncio.TimeoutError:
                last_error = f"Operation timed out after {self.timeout_sec}s"
                logger.warning(f"Tool '{self.name}' timeout on attempt {attempt+1}")
            except ToolError as te:
                last_error = te.message
                if not te.retryable:
                    raise te
                logger.warning(f"Tool '{self.name}' retryable error: {te.message}")
            except Exception as e:
                last_error = str(e)
                logger.exception(f"Tool '{self.name}' unexpected error: {e}")
            
            if attempt < self.max_retries:
                await asyncio.sleep(0.5 * (attempt + 1)) # Exponential backoff
        
        # Final failure
        raise ToolError(f"Failed after {self.max_retries} retries. Last error: {last_error}", agent=self.name)

    async def _run(self, input_data: I, context: Dict[str, Any]) -> Any:
        """Core tool logic to be implemented by subclasses."""
        raise NotImplementedError("Subclasses must implement _run()")

# --- Standard Tool Response Schema ---
class StandardToolOutput(BaseModel):
    """Catch-all schema for tools that return a simple message and data payload."""
    success: bool = True
    message: str = ""
    data: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None
    latency_ms: int = 0
    agent: str = ""
