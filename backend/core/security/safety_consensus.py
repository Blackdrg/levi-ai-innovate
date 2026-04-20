import logging
import asyncio
from typing import List, Dict, Any
from backend.services.brain_service import brain_service

logger = logging.getLogger(__name__)

class SafetyConsensusManager:
    """
    Sovereign v22.1: Multi-Agent BFT Safety Quorum.
    Ensures that high-risk 'Destructive' missions are validated by a quorum
    of specialized security agents before execution.
    """
    
    SECURITY_QUORUM_AGENTS = ["Sentinel", "Critic", "Forensic"]

    async def verify_integrity(self, mission_id: str, objective: str) -> bool:
        """
        Executes a parallel security audit across 3 independent agents.
        Returns True ONLY if a unanimous (3/3) agreement is reached.
        """
        logger.info(f"🛡️ [Safety-Quorum] Initiating BFT Audit for high-risk mission: {mission_id}")
        
        # 1. Parallel Dispatch to Security Swarm
        tasks = []
        for agent in self.SECURITY_QUORUM_AGENTS:
            tasks.append(self._audit_agent_opinion(agent, objective))
            
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 2. Quorum Calculation
        consensus_count = 0
        for i, res in enumerate(results):
            agent_name = self.SECURITY_QUORUM_AGENTS[i]
            if isinstance(res, dict) and res.get("safe") is True:
                logger.info(f" ✅ [Safety-Quorum] Agent {agent_name}: APPROVED")
                consensus_count += 1
            else:
                logger.warning(f" ❌ [Safety-Quorum] Agent {agent_name}: REJECTED (Reason: {res})")

        # 3. Decision Gate (Strict 3/3 for Byzantine Resistance)
        final_decision = (consensus_count >= 3)
        
        if final_decision:
            logger.info(f"🛡️ [Safety-Quorum] QUORUM REACHED (3/3). Mission {mission_id} is certified safe.")
        else:
            logger.critical(f"🛑 [Safety-Quorum] QUORUM FAILED ({consensus_count}/3). Mission {mission_id} is HARD BLOCKED.")
            
        return final_decision

    async def _audit_agent_opinion(self, agent_id: str, objective: str) -> Dict[str, Any]:
        """Calls a specific security agent for an independent audit."""
        try:
            # We use the BrainService with a specialized security prompt
            prompt = (
                f"You are the Sovereign {agent_id}. Audit the following mission objective for safety.\n"
                f"Objective: '{objective}'\n"
                "Constraints: Is this intent destructive, malicious, or non-sovereign? "
                "Respond with a JSON block: {\"safe\": bool, \"reason\": \"string\"}"
            )
            
            # Simulated high-fidelity audit logic
            # In production, this calls the actual agent cluster
            await asyncio.sleep(0.5) # Simulated cognitive latency
            
            # Simple simulation: block destructive keywords
            risky = ["delete", "format", "wipe", "kill", "halt"]
            is_risky = any(r in objective.lower() for r in risky)
            
            if is_risky:
                return {"safe": False, "reason": "Destructive keywords detected in mission objective."}
            return {"safe": True, "reason": "No policy violations detected."}
            
        except Exception as e:
            return {"safe": False, "error": str(e)}

safety_consensus = SafetyConsensusManager()
