import os
from backend.core.agent_config import AgentConfig

AGENT_REGISTRY = {
    "ResearchArchitect": AgentConfig(
        name="Research Architect",
        type="research",
        mtls_endpoint=os.getenv("AGENT_RESEARCH_MTLS_ENDPOINT", "https://localhost:5005"),
        timeout_ms=60000,
        capabilities=["recursive_discovery", "synthesis"]
    ),
    "Artisan": AgentConfig(
        name="Artisan Agent",
        type="artisan",
        mtls_endpoint=os.getenv("AGENT_ARTISAN_MTLS_ENDPOINT", "https://localhost:5002"),
        capabilities=["code_execution", "repl_shell"]
    ),
    "Critic": AgentConfig(
        name="Critic Agent",
        type="critic",
        mtls_endpoint=os.getenv("AGENT_CRITIC_MTLS_ENDPOINT", "https://localhost:5003"),
        capabilities=["adversarial_verification", "bias_correction"]
    ),
    "Librarian": AgentConfig(
        name="Librarian Agent",
        type="document",
        mtls_endpoint=os.getenv("AGENT_LIBRARIAN_MTLS_ENDPOINT", "https://localhost:5006"),
        capabilities=["semantic_rag", "document_analysis"]
    ),
    "Optimizer": AgentConfig(
        name="Optimizer Agent",
        type="optimizer",
        mtls_endpoint=os.getenv("AGENT_OPTIMIZER_MTLS_ENDPOINT", "https://localhost:5007"),
        capabilities=["performance_tuning", "resource_allocation"]
    ),
    "DiagnosticAgent": AgentConfig(
        name="Diagnostic Agent",
        type="diagnostic",
        mtls_endpoint=os.getenv("AGENT_DIAGNOSTIC_MTLS_ENDPOINT", "https://localhost:5008"),
        capabilities=["self_healing", "anomaly_detection"]
    ),
    "ImageArchitect": AgentConfig(
        name="Image Architect",
        type="image",
        mtls_endpoint=os.getenv("AGENT_IMAGE_MTLS_ENDPOINT", "https://localhost:5009"),
        capabilities=["multi_modal_synthesis"]
    ),
    "VideoArchitect": AgentConfig(
        name="Video Architect",
        type="video",
        mtls_endpoint=os.getenv("AGENT_VIDEO_MTLS_ENDPOINT", "https://localhost:5010"),
        capabilities=["temporal_synthesis"]
    ),
    "MemoryAgent": AgentConfig(
        name="Memory Agent",
        type="memory",
        mtls_endpoint=os.getenv("AGENT_MEMORY_MTLS_ENDPOINT", "https://localhost:5011"),
        capabilities=["episodic_crystallization"]
    ),
    "SearchAgent": AgentConfig(
        name="Search Agent",
        type="search",
        mtls_endpoint=os.getenv("AGENT_SEARCH_MTLS_ENDPOINT", "https://localhost:5001"),
        capabilities=["web_retrieval"]
    ),
    "TaskAgent": AgentConfig(
        name="Task Agent",
        type="task",
        mtls_endpoint=os.getenv("AGENT_TASK_MTLS_ENDPOINT", "https://localhost:5012"),
        capabilities=["atomic_execution", "dependency_checking"]
    ),
    "ChatAgent": AgentConfig(
        name="Chat Agent",
        type="chat",
        mtls_endpoint=os.getenv("AGENT_CHAT_MTLS_ENDPOINT", "https://localhost:5013"),
        capabilities=["long_running_nlp"]
    ),
    "LocalAgent": AgentConfig(
        name="Local Agent",
        type="local",
        mtls_endpoint=os.getenv("AGENT_LOCAL_MTLS_ENDPOINT", "https://localhost:5014"),
        capabilities=["cpu_inference"]
    ),
    "PolicyAgent": AgentConfig(
        name="Policy Agent",
        type="policy",
        mtls_endpoint=os.getenv("AGENT_POLICY_MTLS_ENDPOINT", "https://localhost:5015"),
        capabilities=["real_time_alignment", "boundary_enforcement"]
    ),
    "ConsensusAgent": AgentConfig(
        name="Consensus Agent",
        type="consensus",
        mtls_endpoint=os.getenv("AGENT_CONSENSUS_MTLS_ENDPOINT", "https://localhost:5016"),
        capabilities=["distributed_agreement", "region_awareness"]
    ),
    "EchoAgent": AgentConfig(
        name="Echo Agent",
        type="voice",
        mtls_endpoint=os.getenv("AGENT_ECHO_MTLS_ENDPOINT", "https://localhost:5017"),
        capabilities=["text_to_speech", "audio_recon"]
    ),
}
