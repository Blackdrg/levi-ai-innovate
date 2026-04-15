"""
Sovereign Decentralized Governance Engine v16.1 (Task 2.9).
Enables the Hive to vote on model graduations, system parameters, and cognitive policies.
Utilizes the DCN Raft-lite consensus for definitive voting outcomes.
"""

import asyncio
import logging
import json
import time
from typing import Dict, Any, List, Optional
from backend.core.dcn_protocol import get_dcn_protocol
from backend.db.redis import r_async as redis_client

logger = logging.getLogger(__name__)

class GovernanceProposal:
    def __init__(self, proposal_id: str, proposal_type: str, payload: Dict[str, Any]):
        self.proposal_id = proposal_id
        self.proposal_type = proposal_type # e.g., 'model_upgrade', 'policy_change'
        self.payload = payload
        self.votes_for = set()
        self.votes_against = set()
        self.created_at = time.time()

class GovernanceEngine:
    """
    Decentralized Governance for the LEVI Hive.
    Handles the lifecycle of proposals from creation to regional application.
    """
    
    def __init__(self):
        self.dcn = get_dcn_protocol()
    async def _save_proposal(self, proposal_id: str, payload: Dict[str, Any]):
        await redis_client.hset(f"dcn:governance:prop:{proposal_id}", mapping={
            "payload": json.dumps(payload),
            "status": "active",
            "created_at": time.time()
        })

    async def propose_upgrade(self, upgrade_type: str, new_version: str, details: str):
        """Creates a new proposal and broadcasts it to the mesh."""
        proposal_id = f"prop_{int(time.time())}"
        payload = {
            "type": upgrade_type,
            "version": new_version,
            "details": details,
            "proposer": self.dcn.node_id
        }
        
        logger.info(f"🗳️ [Governance] New Proposal: {upgrade_type} -> {new_version} ({proposal_id})")
        
        # Persist locally in Redis
        await self._save_proposal(proposal_id, payload)
        
        await self.dcn.broadcast_gossip(
            mission_id="governance",
            payload={"proposal_id": proposal_id, **payload},
            pulse_type="governance_proposal"
        )

    async def cast_vote(self, proposal_id: str, approve: bool = True):
        """Casts a vote on an active proposal."""
        logger.info(f"🗳️ [Governance] Casting {'APPROVE' if approve else 'REJECT'} on {proposal_id}")
        
        await self.dcn.broadcast_gossip(
            mission_id="governance",
            payload={"proposal_id": proposal_id, "vote": "approve" if approve else "reject"},
            pulse_type="governance_vote"
        )

    async def handle_proposal_pulse(self, payload: Dict[str, Any]):
        """Callback for incoming proposals from the mesh."""
        proposal_id = payload.get("proposal_id")
        exists = await redis_client.exists(f"dcn:governance:prop:{proposal_id}")
        if not exists:
            logger.info(f"🗳️ [Governance] Discovered new mesh proposal: {proposal_id}")
            await self._save_proposal(proposal_id, payload)

    async def handle_vote_pulse(self, sender_id: str, payload: Dict[str, Any]):
        """Callback for incoming votes from the mesh."""
        proposal_id = payload.get("proposal_id")
        vote = payload.get("vote")
        
        prop_key = f"dcn:governance:prop:{proposal_id}"
        if await redis_client.exists(prop_key):
            vote_key = f"dcn:governance:votes:{proposal_id}:{'for' if vote == 'approve' else 'against'}"
            await redis_client.sadd(vote_key, sender_id)
            
            votes_for_count = await redis_client.scard(f"dcn:governance:votes:{proposal_id}:for")
            logger.debug(f"🗳️ [Governance] Votes for {proposal_id}: {votes_for_count}")
            
            # Check for Quorum
            if self.dcn.verify_quorum(votes_for_count):
                # Load payload for finalization
                prop_data = await redis_client.hgetall(prop_key)
                if prop_data.get(b"status") == b"active":
                    await redis_client.hset(prop_key, "status", "graduated")
                    payload = json.loads(prop_data[b"payload"].decode())
                    await self._finalize_proposal(proposal_id, payload)

    async def _finalize_proposal(self, proposal_id: str, payload: Dict[str, Any]):
        """Applies the proposal once consensus is reached."""
        logger.info(f"🏆 [Governance] Proposal {proposal_id} passed! Finalizing...")
        
        proposal_type = payload.get("type")
        if proposal_type == "model_upgrade":
            # Logic to update ModelRouter or pull new weights
            logger.info(f"🚀 [Upgrade] Model graduated to {payload.get('version')}")
             # We would broadcast a Raft pulse here to ensure all nodes apply it
            await self.dcn.broadcast_mission_truth(
                mission_id=f"finalize_{proposal_id}",
                outcome={"status": "graduated", "version": payload.get("version")}
            )
        
        elif proposal_type == "personality_drift":
            from backend.core.identity import identity_system
            await identity_system.apply_governance_result(proposal_type, payload)
            logger.info(f"🧬 [Governance] Personality drift applied for {proposal_id}")

governance_engine = GovernanceEngine()
