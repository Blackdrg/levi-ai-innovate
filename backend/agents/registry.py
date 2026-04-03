"""
Sovereign Agent Registry v8.
Centralized mapping for autonomous cognitive agents.
"""

from backend.core.v8.agents.research import ResearchAgentV8
from backend.core.v8.agents.code import CodeAgentV8
from backend.core.v8.agents.document import DocumentAgentV8
from backend.core.v8.agents.chat import ChatAgentV8
from backend.core.v8.agents.python_repl import PythonReplAgentV8

AGENT_REGISTRY = {
    "research": ResearchAgentV8(),
    "code": CodeAgentV8(),
    "document": DocumentAgentV8(),
    "chat": ChatAgentV8(),
    "python": PythonReplAgentV8(),
}

# Alias for compatibility with simple registry patterns
ResearchAgent = ResearchAgentV8
CodeAgent = CodeAgentV8
DocumentAgent = DocumentAgentV8
