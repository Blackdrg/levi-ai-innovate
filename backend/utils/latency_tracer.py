import logging
import time
from contextlib import asynccontextmanager
from typing import Dict, List

logger = logging.getLogger(__name__)


class LatencyTracer:
    """Collect coarse end-to-end latency segments for a mission."""

    def __init__(self):
        self.segments: List[Dict[str, float]] = []

    @asynccontextmanager
    async def trace(self, segment_name: str):
        start = time.perf_counter()
        try:
            yield
        finally:
            elapsed_ms = (time.perf_counter() - start) * 1000
            self.segments.append({"segment": segment_name, "latency_ms": elapsed_ms})
            logger.info("[LatencyTracer] %s=%.1fms", segment_name, elapsed_ms)

    def report(self) -> Dict[str, float]:
        return {segment["segment"]: round(segment["latency_ms"], 2) for segment in self.segments}

    def total(self) -> float:
        return round(sum(segment["latency_ms"] for segment in self.segments), 2)
