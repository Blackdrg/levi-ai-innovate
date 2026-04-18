import os
from backend.core.agent_config import AgentConfig

AGENT_REGISTRY = {
    "Sovereign": AgentConfig(
        name="Sovereign Coordinator",
        type="sovereign",
        mtls_endpoint=os.getenv("AGENT_SOVEREIGN_MTLS_ENDPOINT", "https://localhost:5000"),
        capabilities=["orchestration", "goal_decomposition"]
    ),
    "Architect": AgentConfig(
        name="Research Architect",
        type="architect",
        mtls_endpoint=os.getenv("AGENT_ARCHITECT_MTLS_ENDPOINT", "https://localhost:5005"),
        capabilities=["recursive_discovery", "synthesis", "dag_design"]
    ),
    "Librarian": AgentConfig(
        name="Librarian Agent",
        type="librarian",
        mtls_endpoint=os.getenv("AGENT_LIBRARIAN_MTLS_ENDPOINT", "https://localhost:5006"),
        capabilities=["semantic_rag", "document_analysis", "memory_indexing"]
    ),
    "Artisan": AgentConfig(
        name="Artisan Agent",
        type="artisan",
        mtls_endpoint=os.getenv("AGENT_ARTISAN_MTLS_ENDPOINT", "https://localhost:5002"),
        capabilities=["code_execution", "repl_shell", "tool_creation"]
    ),
    "Analyst": AgentConfig(
        name="Data Analyst",
        type="analyst",
        mtls_endpoint=os.getenv("AGENT_ANALYST_MTLS_ENDPOINT", "https://localhost:5007"),
        capabilities=["pattern_recognition", "statistical_audit"]
    ),
    "Critic": AgentConfig(
        name="Critic Agent",
        type="critic",
        mtls_endpoint=os.getenv("AGENT_CRITIC_MTLS_ENDPOINT", "https://localhost:5003"),
        capabilities=["adversarial_verification", "bias_correction", "fidelity_rating"]
    ),
    "Sentinel": AgentConfig(
        name="Sentinel Security",
        type="sentinel",
        mtls_endpoint=os.getenv("AGENT_SENTINEL_MTLS_ENDPOINT", "https://localhost:5008"),
        capabilities=["self_healing", "anomaly_detection", "firewall_governance"]
    ),
    "Dreamer": AgentConfig(
        name="Dreamer Engine",
        type="dreamer",
        mtls_endpoint=os.getenv("AGENT_DREAMER_MTLS_ENDPOINT", "https://localhost:5011"),
        capabilities=["evolutionary_distillation", "creative_synthesis"]
    ),
    "Scout": AgentConfig(
        name="Scout Search",
        type="scout",
        mtls_endpoint=os.getenv("AGENT_SCOUT_MTLS_ENDPOINT", "https://localhost:5001"),
        capabilities=["web_retrieval", "real_time_tracking"]
    ),
    "Historian": AgentConfig(
        name="Historian Chronicler",
        type="historian",
        mtls_endpoint=os.getenv("AGENT_HISTORIAN_MTLS_ENDPOINT", "https://localhost:5012"),
        capabilities=["long_term_ledger", "context_continuity"]
    ),
    "Vision": AgentConfig(
        name="Vision Multimodal",
        type="vision",
        mtls_endpoint=os.getenv("AGENT_VISION_MTLS_ENDPOINT", "https://localhost:5009"),
        capabilities=["multi_modal_synthesis", "spatial_reasoning"]
    ),
    "Echo": AgentConfig(
        name="Echo Audio",
        type="echo",
        mtls_endpoint=os.getenv("AGENT_ECHO_MTLS_ENDPOINT", "https://localhost:5017"),
        capabilities=["text_to_speech", "audio_recon", "vocal_cloning"]
    ),
    "Forensic": AgentConfig(
        name="Forensic Auditor",
        type="forensic",
        mtls_endpoint=os.getenv("AGENT_FORENSIC_MTLS_ENDPOINT", "https://localhost:5018"),
        capabilities=["non_repudiation", "tamper_detection"]
    ),
    "Healer": AgentConfig(
        name="Healer Physician",
        type="healer",
        mtls_endpoint=os.getenv("AGENT_HEALER_MTLS_ENDPOINT", "https://localhost:5019"),
        capabilities=["autonomous_refactor", "bug_healing"]
    ),
    "Consensus": AgentConfig(
        name="Consensus Pulse",
        type="consensus",
        mtls_endpoint=os.getenv("AGENT_CONSENSUS_MTLS_ENDPOINT", "https://localhost:5016"),
        capabilities=["distributed_agreement", "region_awareness"]
    ),
    "Identity": AgentConfig(
        name="Identity Guard",
        type="identity",
        mtls_endpoint=os.getenv("AGENT_IDENTITY_MTLS_ENDPOINT", "https://localhost:5015"),
        capabilities=["real_time_alignment", "boundary_enforcement", "persona_lock"]
    ),
}
