from __future__ import annotations

import asyncio
import logging
import os
from typing import Coroutine, Set

logger = logging.getLogger(__name__)

_tracked_tasks: Set[asyncio.Task] = set()
_shutting_down = False


def is_shutting_down() -> bool:
    return _shutting_down


def create_tracked_task(coro: Coroutine, *, name: str) -> asyncio.Task:
    """
    Register background tasks so shutdown can wait for in-flight work to drain.
    """
    global _shutting_down
    if _shutting_down:
        raise RuntimeError("Runtime is shutting down; refusing to schedule new background work.")

    task = asyncio.create_task(coro, name=name)
    _tracked_tasks.add(task)

    def _cleanup(done_task: asyncio.Task) -> None:
        _tracked_tasks.discard(done_task)
        try:
            done_task.result()
        except asyncio.CancelledError:
            logger.info("Background task cancelled during shutdown: %s", done_task.get_name())
        except Exception:
            logger.exception("Background task failed: %s", done_task.get_name())

    task.add_done_callback(_cleanup)
    return task


async def begin_shutdown(*, timeout: float | None = None) -> None:
    """
    Stop accepting new background work and wait for tracked tasks to finish.
    """
    global _shutting_down
    _shutting_down = True

    pending = [task for task in list(_tracked_tasks) if not task.done()]
    if not pending:
        return

    wait_timeout = timeout if timeout is not None else float(os.getenv("GRACEFUL_SHUTDOWN_TIMEOUT_SECONDS", "30"))
    done, not_done = await asyncio.wait(pending, timeout=wait_timeout)
    for task in not_done:
        logger.warning("Cancelling undrained background task after timeout: %s", task.get_name())
        task.cancel()
    if not_done:
        await asyncio.gather(*not_done, return_exceptions=True)
    if done:
        await asyncio.gather(*done, return_exceptions=True)


def reset_runtime_state() -> None:
    """
    Test helper.
    """
    global _shutting_down
    _tracked_tasks.clear()
    _shutting_down = False
