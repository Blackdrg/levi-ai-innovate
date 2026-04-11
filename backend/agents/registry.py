"""
Sovereign Agent Registry v9.
Centralized mapping for autonomous cognitive agents.
All agents are fully wired — no stubs remain.
"""

from .research_agent  import ResearchAgent
from .code_agent      import CodeAgent
from .search_agent    import SearchAgent
from .critic_agent    import CriticAgent
from .python_repl_agent import PythonReplAgent
from .document_agent  import DocumentAgent
from .task_agent      import TaskAgent
from .consensus_agent import ConsensusAgentV11
from .optimizer_agent import OptimizerAgent
from .memory_agent    import MemoryAgent
from .diagnostic_agent import DiagnosticAgent
from .image_agent     import ImageAgent
from .video_agent     import VideoAgent
from .relay_agent     import RelayAgent
from .artisan_agent   import ArtisanAgent
from .scout_agent     import ScoutAgent
from .hard_rule_agent import HardRuleAgent

AGENT_REAGENT_MAP = {
    # Core Logic
    "artisan": "ArtisanAgent",
    "scout": "ScoutAgent",
    "critic": "CriticAgent",
    "coder": "CoderAgent",
    "researcher": "ResearcherAgent",
    "analyst": "AnalystAgent",
    "hard_rule": "HardRuleAgent",
    "swarm_ctrl": "SwarmCtrlAgent",
    "optimizer": "OptimizerAgent",
    "memory": "MemoryAgent",
    "diagnostic": "DiagnosticAgent",
    "relay": "RelayAgent",
    
    # Multimedia
    "imaging": "ImagingAgent",
    "video": "VideoAgent"
}

AGENT_REGISTRY = {
    "Artisan": ArtisanAgent(),
    "Scout": ScoutAgent(),
    "Critic": CriticAgent(),
    "Coder": PythonReplAgent(),
    "Researcher": ResearchAgent(),
    "Analyst": DocumentAgent(),
    "HardRule": HardRuleAgent(),
    "SwarmCtrl": ConsensusAgentV11(),
    "Optimizer": OptimizerAgent(),
    "Memory": MemoryAgent(),
    "Diagnostic": DiagnosticAgent(),
    "Imaging": ImageAgent(),
    "Video": VideoAgent(),
    "Relay": RelayAgent(),
}
