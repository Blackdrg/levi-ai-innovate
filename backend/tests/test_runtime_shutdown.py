from __future__ import annotations

import asyncio

import pytest

from backend.utils.runtime_tasks import begin_shutdown, create_tracked_task, reset_runtime_state


@pytest.fixture(autouse=True)
def _reset_runtime_state():
    reset_runtime_state()
    yield
    reset_runtime_state()


@pytest.mark.asyncio
async def test_begin_shutdown_drains_and_cancels_tracked_tasks():
    started = asyncio.Event()
    cancelled = asyncio.Event()

    async def slow_task():
        started.set()
        try:
            await asyncio.sleep(10)
        except asyncio.CancelledError:
            cancelled.set()
            raise

    create_tracked_task(slow_task(), name="slow-task")
    await started.wait()
    await begin_shutdown(timeout=0.05)

    assert cancelled.is_set()


@pytest.mark.asyncio
async def test_cannot_schedule_new_background_task_after_shutdown():
    await begin_shutdown(timeout=0)
    late_coro = asyncio.sleep(0)

    with pytest.raises(RuntimeError):
        create_tracked_task(late_coro, name="late-task")
    late_coro.close()
