import pytest
import asyncio
from backend.utils.runtime_tasks import create_tracked_task, begin_shutdown, reset_runtime_state, _tracked_tasks

@pytest.mark.asyncio
async def test_shutdown_drain_waits_for_tasks():
    # Setup
    reset_runtime_state()
    task_finished = False

    async def slow_task():
        nonlocal task_finished
        await asyncio.sleep(0.5)
        task_finished = True

    # Register task
    create_tracked_task(slow_task(), name="test_slow_task")
    assert len(_tracked_tasks) == 1

    # Initiate shutdown
    await begin_shutdown(timeout=2.0)

    # Verify task completed properly and wasn't orphaned
    assert task_finished is True
    assert len(_tracked_tasks) == 0

@pytest.mark.asyncio
async def test_shutdown_drain_cancels_on_timeout():
    # Setup
    reset_runtime_state()
    
    async def very_slow_task():
        await asyncio.sleep(10.0)

    # Register task
    create_tracked_task(very_slow_task(), name="test_very_slow_task")
    
    # Initiate shutdown with brief timeout
    await begin_shutdown(timeout=0.1)

    # Task should be cancelled and drained from the set
    assert len(_tracked_tasks) == 0
