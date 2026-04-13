"""
LEVI-AI Evolution Module.
Framework for Self-Monitoring, Continuous Learning, and Autonomous Self-Mutation.
[DISABLED] - Replaced by Phase 2 Learning Loop (backend/core/learning_loop.py).
Implemented for future weeks 17-40 research.
"""

from .monitor import monitor as self_monitor
from .analyzer import analyzer as failure_analyzer
from .learning import learner as success_learner
from .optimizer import optimizer as parameter_optimizer
from .mutator import algorithm_mutator, strategy_mutator
from .discovery import discovery_engine

__all__ = [
    "self_monitor",
    "failure_analyzer",
    "success_learner",
    "parameter_optimizer",
    "algorithm_mutator",
    "strategy_mutator",
    "discovery_engine"
]
