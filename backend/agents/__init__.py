"""
Sovereign Agent Ecosystem v8.
Contains autonomous agents for specialized cognitive tasks.
"""

REGISTERED_AGENTS = [
    "Artisan",    # CodeGen
    "Scout",      # Research / web
    "Critic",     # Adjudicator
    "Coder",      # Logic
    "Researcher", # Discovery
    "Analyst",    # Quant
    "HardRule",   # Validator
    "SwarmCtrl",  # Sub-mission gateway
    "Optimizer",  # Efficiency
    "Memory",     # Long-term retrieval
    "Diagnostic", # System health
    "Imaging",    # Vision/Generation
    "Video",      # Motion Synthesis
    "Relay",      # Sub-mission handoff router
]

AGENT_COUNT = len(REGISTERED_AGENTS)  # single source of truth (14)
    
from .base import SovereignAgent as BaseAgent
from .code_agent import CodeAgent as Artisan
from .search_agent import SearchAgent as Scout
from .critic_agent import CriticAgent as Critic
from .python_repl_agent import PythonReplAgent as Coder
from .research_agent import ResearchAgent as Researcher
from .document_agent import DocumentAgent as Analyst
from .task_agent import TaskAgent as HardRule
from .consensus_agent import ConsensusAgentV14 as SwarmCtrl
from .optimizer_agent import OptimizerAgent as Optimizer
from .memory_agent import MemoryAgent as Memory
from .diagnostic_agent import DiagnosticAgent as Diagnostic
from .image_agent import ImageAgent as Imaging
from .video_agent import VideoAgent as Video
from .relay_agent import RelayAgent as Relay
