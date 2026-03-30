from typing import Any, Callable, Dict, Optional

# Global registry for the broadcast function to avoid circular imports
_broadcast_func: Optional[Callable[[str, Dict[str, Any]], None]] = None
_instance_id: Optional[str] = None

def register_broadcaster(func: Callable[[str, Dict[str, Any]], None], instance_id: str) -> None:
    """Register the gateway's broadcast function."""
    global _broadcast_func, _instance_id
    _broadcast_func = func
    _instance_id = instance_id

def broadcast_activity(event_type: str, data: Dict[str, Any]):
    """Proxy function to broadcast activity without importing the gateway."""
    if _broadcast_func:
        _broadcast_func(event_type, data)
    else:
        # Fallback or silent skip if not registered yet
        pass
