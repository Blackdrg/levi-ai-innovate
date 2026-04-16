"""Core event bus entrypoint.

This module exists so new foundation code can depend on a stable core path while
legacy callers continue to use ``backend.utils.event_bus``.
"""

from backend.utils.event_bus import SovereignEventBus, sovereign_event_bus as event_bus

__all__ = ["SovereignEventBus", "event_bus"]
