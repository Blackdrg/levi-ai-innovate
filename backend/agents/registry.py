import os
from backend.core.agent_config import AgentConfig

# Sovereign v22.1: The 16-Agent Swarm Registry
# Each agent is an isolated cognitive unit with specific axioms and implementation.
# Capabilities define the mission-routing logic in the Orchestrator.

AGENT_REGISTRY = {
    "Sovereign": AgentConfig(
        name="Sovereign Coordinator",
        type="sovereign",
        mtls_endpoint=os.getenv("AGENT_SOVEREIGN_MTLS_ENDPOINT", "https://localhost:5000"),
        capabilities=["orchestration", "security_enforcement", "admission_control"]
    ),
    "Architect": AgentConfig(
        name="Mission Architect",
        type="architect",
        mtls_endpoint=os.getenv("AGENT_ARCHITECT_MTLS_ENDPOINT", "https://localhost:5001"),
        capabilities=["mission_planning", "dag_generation", "task_decomposition"]
    ),
    "Artisan": AgentConfig(
        name="Artisan Builder",
        type="artisan",
        mtls_endpoint=os.getenv("AGENT_ARTISAN_MTLS_ENDPOINT", "https://localhost:5002"),
        capabilities=["code_execution", "repl_shell", "tool_creation", "sandboxed_logic"]
    ),
    "Analyst": AgentConfig(
        name="Logic Analyst",
        type="analyst",
        mtls_endpoint=os.getenv("AGENT_ANALYST_MTLS_ENDPOINT", "https://localhost:5003"),
        capabilities=["pattern_recognition", "logical_synthesis", "gap_analysis"]
    ),
    "Critic": AgentConfig(
        name="Gatekeeper Critic",
        type="critic",
        mtls_endpoint=os.getenv("AGENT_CRITIC_MTLS_ENDPOINT", "https://localhost:5004"),
        capabilities=["adversarial_verification", "hallucination_detection", "fidelity_rating"]
    ),
    "Sentinel": AgentConfig(
        name="Frontier Sentinel",
        type="sentinel",
        mtls_endpoint=os.getenv("AGENT_SENTINEL_MTLS_ENDPOINT", "https://localhost:5005"),
        capabilities=["prompt_injection_defense", "noise_filtering", "security_screening"]
    ),
    "Historian": AgentConfig(
        name="Immutable Historian",
        type="chronicler",
        mtls_endpoint=os.getenv("AGENT_HISTORIAN_MTLS_ENDPOINT", "https://localhost:5006"),
        capabilities=["episodic_memory", "trace_recording", "hmac_chaining"]
    ),
    "Forensic": AgentConfig(
        name="Integrity Auditor",
        type="forensic",
        mtls_endpoint=os.getenv("AGENT_FORENSIC_MTLS_ENDPOINT", "https://localhost:5007"),
        capabilities=["audit_ledger_verification", "checksum_auditing", "lockdown_trigger"]
    ),
    "Nomad": AgentConfig(
        name="DCN Bridge",
        type="nomad",
        mtls_endpoint=os.getenv("AGENT_NOMAD_MTLS_ENDPOINT", "https://localhost:5008"),
        capabilities=["cross_region_sync", "mesh_gossip", "mtls_management"]
    ),
    "Thermal": AgentConfig(
        name="Hardware Guardian",
        type="thermal",
        mtls_endpoint=os.getenv("AGENT_THERMAL_MTLS_ENDPOINT", "https://localhost:5009"),
        capabilities=["thermal_monitoring", "vram_throttling", "swarm_migration"]
    ),
    "Epistemic": AgentConfig(
        name="Knowledge Resonator",
        type="epistemic",
        mtls_endpoint=os.getenv("AGENT_EPISTEMIC_MTLS_ENDPOINT", "https://localhost:5010"),
        capabilities=["fact_graduation", "semantic_resonance", "t4_crystallization"]
    ),
    "Pulse": AgentConfig(
        name="Heartbeat Sync",
        type="pulse",
        mtls_endpoint=os.getenv("AGENT_PULSE_MTLS_ENDPOINT", "https://localhost:5011"),
        capabilities=["temporal_alignment", "latency_monitoring", "node_failure_detection"]
    ),
    "Shield": AgentConfig(
        name="Privacy Shield",
        type="shield",
        mtls_endpoint=os.getenv("AGENT_SHIELD_MTLS_ENDPOINT", "https://localhost:5012"),
        capabilities=["pii_masking", "kms_encryption", "privacy_preservation"]
    ),
    "Shadow": AgentConfig(
        name="Redundancy Shadow",
        type="shadow",
        mtls_endpoint=os.getenv("AGENT_SHADOW_MTLS_ENDPOINT", "https://localhost:5013"),
        capabilities=["redundant_execution", "silent_error_detection", "bit_flip_verification"]
    ),
    "Hive": AgentConfig(
        name="Swarm Collective",
        type="hive",
        mtls_endpoint=os.getenv("AGENT_HIVE_MTLS_ENDPOINT", "https://localhost:5014"),
        capabilities=["swarm_consensus", "unified_resonance", "global_synthesis"]
    ),
    "Genesis": AgentConfig(
        name="Root Bootstrapper",
        type="genesis",
        mtls_endpoint=os.getenv("AGENT_GENESIS_MTLS_ENDPOINT", "https://localhost:5015"),
        capabilities=["system_initialization", "kernel_verification", "swarm_awakening"]
    ),
}
