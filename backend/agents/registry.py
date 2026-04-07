"""
Sovereign Agent Registry v8.
Centralized mapping for autonomous cognitive agents.
"""

from .research_agent import ResearchAgent
from .code_agent import CodeAgent
from .search_agent import SearchAgent
from .critic_agent import CriticAgent
from .python_repl_agent import PythonReplAgent
from .document_agent import DocumentAgent
from .task_agent import TaskAgent
from .consensus_agent import ConsensusAgentV11
from .optimizer_agent import OptimizerAgent
from .memory_agent import MemoryAgent
from .diagnostic_agent import DiagnosticAgent
from .image_agent import ImageAgent
from .video_agent import VideoAgent

class RelayAgentStub:
    async def execute(self, *args, **kwargs):
        return {"success": True, "message": "Relay stub - no action taken."}

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
    "Artisan": CodeAgent(),
    "Scout": SearchAgent(),
    "Critic": CriticAgent(),
    "Coder": PythonReplAgent(),
    "Researcher": ResearchAgent(),
    "Analyst": DocumentAgent(),
    "HardRule": TaskAgent(),
    "SwarmCtrl": ConsensusAgentV11(),
    "Optimizer": OptimizerAgent(),
    "Memory": MemoryAgent(),
    "Diagnostic": DiagnosticAgent(),
    "Imaging": ImageAgent(),
    "Video": VideoAgent(),
    "Relay": RelayAgentStub(),
}
