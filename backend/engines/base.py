import abc
import logging
import time
import asyncio
from typing import Any, Dict, List, Optional
from pydantic import BaseModel

logger = logging.getLogger(__name__)

class EngineResult(BaseModel):
    """Standardized output for all Sovereign Engines."""
    status: str = "success"
    data: Any = None
    metadata: Dict[str, Any] = {}
    error: Optional[str] = None
    latency_ms: float = 0.0

class EngineBase(abc.ABC):
    """
    Abstract Base Class for all LEVI-AI Sovereign Engines.
    Provides standardized logging, performance tracking, and global-ready utilities.
    """
    
    def __init__(self, name: str):
        self.name = name
        self.logger = logging.getLogger(f"engine.{name.lower()}")
        self._initialize_i18n()

    def _initialize_i18n(self):
        """Sets up engine-level internationalization."""
        # Future: Load engine-specific translation bundles
        pass

    async def execute(self, **kwargs) -> EngineResult:
        """
        Main execution wrapper with telemetry and error isolation.
        """
        start_time = time.perf_counter()
        self.logger.info(f"Engine {self.name} started task.")
        
        try:
            # Call the actual implementation in the child class
            result_data = await self._run(**kwargs)
            
            latency = (time.perf_counter() - start_time) * 1000
            return EngineResult(
                status="success",
                data=result_data,
                latency_ms=latency,
                metadata={"engine": self.name}
            )
            
        except Exception as e:
            latency = (time.perf_counter() - start_time) * 1000
            self.logger.error(f"Engine {self.name} failure: {str(e)}", exc_info=True)
            return EngineResult(
                status="error",
                error=str(e),
                latency_ms=latency,
                metadata={"engine": self.name}
            )

    @abc.abstractmethod
    async def _run(self, **kwargs) -> Any:
        """Internal implementation to be overridden by subclasses."""
        pass

    def log_telemetry(self, flow_id: str, metric_name: str, value: Any):
        """Standardized metric reporting for the Brain Learning Loop."""
        self.logger.debug(f"Telemetry [{flow_id}] {metric_name}: {value}")
