"""
backend/core/memory — Memory Resonance Package

Exports the MemoryResonanceManager singleton accessor.
"""

from .resonance_manager import MemoryResonanceManager, get_resonance_manager

__all__ = ["MemoryResonanceManager", "get_resonance_manager"]
