import os
from backend.core.agent_config import AgentConfig

AGENT_REGISTRY = {
    "Artisan": AgentConfig(
        name="Artisan Agent",
        type="artisan",
        mtls_endpoint=os.getenv("AGENT_ARTISAN_MTLS_ENDPOINT", "https://localhost:5002"),
        sandbox_image="python:3.10-slim",
        capabilities=["code_execution", "file_management"]
    ),
    "Scout": AgentConfig(
        name="Scout Agent",
        type="scout",
        mtls_endpoint=os.getenv("AGENT_SCOUT_MTLS_ENDPOINT", "https://localhost:5001"),
        timeout_ms=15000,
        capabilities=["web_search", "crawling"]
    ),
    "Critic": AgentConfig(
        name="Critic Agent",
        type="critic",
        mtls_endpoint=os.getenv("AGENT_CRITIC_MTLS_ENDPOINT", "https://localhost:5003"),
        capabilities=["plan_critique", "validation"]
    ),
    "Coder": AgentConfig(
        name="Coder Agent",
        type="coder",
        mtls_endpoint=os.getenv("AGENT_CODER_MTLS_ENDPOINT", "https://localhost:5004"),
        sandbox_image="python:3.10-slim-buster",
        capabilities=["low_level_code", "debugging"]
    ),
    "Researcher": AgentConfig(
        name="Researcher Agent",
        type="researcher",
        mtls_endpoint=os.getenv("AGENT_RESEARCH_MTLS_ENDPOINT", "https://localhost:5005"),
        timeout_ms=60000,
        capabilities=["deep_research", "synthesis"]
    ),
    "Analyst": AgentConfig(
        name="Analyst Agent",
        type="analyst",
        mtls_endpoint=os.getenv("AGENT_ANALYST_MTLS_ENDPOINT", "https://localhost:5006"),
        capabilities=["document_analysis", "nlp"]
    ),
}
