"""
Sovereign Agent Ecosystem v22.1 [GA].
Standardized 16-agent swarm for the Sovereign OS Engineering Baseline.
"""

# The Unified 16-Agent Swarm (Axiom-Aligned)
REGISTERED_AGENTS = [
    "Sovereign",
    "Architect",
    "Artisan",
    "Analyst",
    "Critic",
    "Sentinel",
    "Historian",
    "Forensic",
    "Nomad",
    "Thermal",
    "Epistemic",
    "Pulse",
    "Shield",
    "Shadow",
    "Hive",
    "Genesis"
]

AGENT_COUNT = len(REGISTERED_AGENTS) # 16

# ── Import Map ──────────────────────────────────────────────────────────────

# Note: 'Sovereign' is internalized in backend/core/orchestrator.py
# and is not typically imported as a standalone agent file.

from .architect import ArchitectAgent as Architect
from .artisan_agent import ArtisanAgent as Artisan
from .analyst import AnalystAgent as Analyst
from .critic import CriticAgent as Critic
from .sentinel import SentinelAgent as Sentinel
from .chronicler import ChroniclerAgent as Historian
from .forensic import ForensicAgent as Forensic
from .nomad import NomadAgent as Nomad
from .thermal import ThermalAgent as Thermal
from .epistemic import EpistemicAgent as Epistemic
from .pulse import PulseAgent as Pulse
from .shield import ShieldAgent as Shield
from .shadow import ShadowAgent as Shadow
from .hive import HiveAgent as Hive
from .genesis import GenesisAgent as Genesis
