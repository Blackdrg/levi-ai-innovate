from pydantic import BaseModel
from typing import List, Optional

class TelemetryPulse(BaseModel):
    event: str = "mission_update"
    mission_id: str
    status: str
    current_wave: int          # required — was missing in 4.10
    active_agents: List[str]
    cu_consumed: float
    fidelity_score: float
    resource_saturation: str
    latencies: dict
    version: str = "v13.1.0-Hardened-PROD"
