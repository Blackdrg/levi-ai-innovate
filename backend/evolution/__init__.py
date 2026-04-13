"""
LEVI-AI Evolution Module.
Framework for Self-Monitoring, Continuous Learning, and Autonomous Self-Mutation.
Implementing Weeks 17-40 of the Revolutionary Innovation Roadmap.
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
