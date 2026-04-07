import asyncio
import logging
import time
from typing import Dict, Any, Callable

logger = logging.getLogger(__name__)

class DynamicBatcher:
    """
    Sovereign Dynamic Batching Engine v14.0.0.
    Optimizes GPU throughput by grouping concurrent cognitive pulses.
    """

    def __init__(self, batch_timeout_ms: int = 50, max_batch_size: int = 8):
        self.batch_timeout = batch_timeout_ms / 1000.0
        self.max_batch_size = max_batch_size
        self.queues: Dict[str, asyncio.Queue] = {}
        self.lock = asyncio.Lock()

    async def execute_batched(self, tier: str, payload: Any, handler: Callable) -> Any:
        """
        Submits a task for batched execution.
        If a batch is filling, it waits. If it's the first, it starts the timer.
        """
        async with self.lock:
            if tier not in self.queues:
                self.queues[tier] = asyncio.Queue()
                # Start a consumer for this tier
                asyncio.create_task(self._batch_processor(tier, handler))

        # Create a future to receive the result
        future = asyncio.get_event_loop().create_future()
        await self.queues[tier].put((payload, future))
        
        return await future

    async def _batch_processor(self, tier: str, handler: Callable):
        """Background loop that drains the queue in batches."""
        logger.info(f"[Batcher] Processor started for tier: {tier}")
        
        while True:
            batch = []
            futures = []
            
            # Wait for the first item
            payload, future = await self.queues[tier].get()
            batch.append(payload)
            futures.append(future)
            
            # Start timer for remaining batch slots
            start_time = time.time()
            
            while len(batch) < self.max_batch_size and (time.time() - start_time) < self.batch_timeout:
                try:
                    # Non-blocking check for more items
                    # We use a short timeout for the wait
                    payload, future = await asyncio.wait_for(self.queues[tier].get(), timeout=self.batch_timeout/5)
                    batch.append(payload)
                    futures.append(future)
                except (asyncio.TimeoutError, asyncio.QueueEmpty):
                    break

            # Execute batch
            if batch:
                logger.debug(f"[Batcher] Executing batch of {len(batch)} for {tier}")
                try:
                    # In this v1, we still call the handler. 
                    # If the handler supports real batching, we'd pass the whole list.
                    # For now, we run them in parallel to maximize IO/GPU pipelining.
                    tasks = [handler(p) for p in batch]
                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    
                    for future, res in zip(futures, results):
                        if not future.done():
                            future.set_result(res)
                except Exception as e:
                    logger.error(f"[Batcher] Batch execution explosion: {e}")
                    for future in futures:
                        if not future.done():
                            future.set_exception(e)
            
            # Yield for a moment
            await asyncio.sleep(0.01)
