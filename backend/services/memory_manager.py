# backend/services/memory_manager.py
"""
Compatibility shim — re-exports MemoryManager from its canonical location.
All imports that use 'backend.services.memory_manager' work without change.
"""
from backend.core.memory_manager import MemoryManager  # noqa: F401

__all__ = ["MemoryManager"]
