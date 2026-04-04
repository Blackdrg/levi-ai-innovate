"""
Sovereign Agent Registry v8.
Centralized mapping for autonomous cognitive agents.
"""

from .research_agent import ResearchAgent
from .code_agent import CodeAgent
from .document_agent import DocumentAgent
from .chat_agent import ChatAgent
from .python_repl_agent import PythonReplAgent
from .consensus_agent import ConsensusAgentV11 as ConsensusAgentV8
from .critic_agent import CriticAgent

AGENT_REGISTRY = {
    "research": ResearchAgent(),
    "code": CodeAgent(),
    "document": DocumentAgent(),
    "chat": ChatAgent(),
    "python": PythonReplAgent(),
    "consensus": ConsensusAgentV8(),
    "critic": CriticAgent(),
}
