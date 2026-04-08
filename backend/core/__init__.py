"""
Lazy core package exports to avoid importing the full legacy engine graph on package import.
"""

__all__ = ["run_orchestrator", "LeviOrchestrator"]


def __getattr__(name):
    if name in __all__:
        from .engine import LeviOrchestrator, run_orchestrator

        exports = {
            "run_orchestrator": run_orchestrator,
            "LeviOrchestrator": LeviOrchestrator,
        }
        return exports[name]
    raise AttributeError(name)
