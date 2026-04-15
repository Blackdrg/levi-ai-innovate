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
        self.active_proposals: Dict[str, GovernanceProposal] = {}

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
        
        await self.dcn.broadcast_gossip(
            mission_id="governance",
            payload={"proposal_id": proposal_id, **payload},
            pulse_type="governance_proposal"
        )
        
        # Initialize locally
        self.active_proposals[proposal_id] = GovernanceProposal(proposal_id, upgrade_type, payload)

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
        if proposal_id not in self.active_proposals:
            logger.info(f"🗳️ [Governance] Discovered new mesh proposal: {proposal_id}")
            self.active_proposals[proposal_id] = GovernanceProposal(
                proposal_id, payload.get("type"), payload
            )

    async def handle_vote_pulse(self, sender_id: str, payload: Dict[str, Any]):
        """Callback for incoming votes from the mesh."""
        proposal_id = payload.get("proposal_id")
        vote = payload.get("vote")
        
        if proposal_id in self.active_proposals:
            prop = self.active_proposals[proposal_id]
            if vote == "approve":
                prop.votes_for.add(sender_id)
            else:
                prop.votes_against.add(sender_id)
            
            logger.debug(f"🗳️ [Governance] Votes for {proposal_id}: {len(prop.votes_for)}")
            
            # Check for Quorum
            if self.dcn.verify_quorum(len(prop.votes_for)):
                await self._finalize_proposal(prop)

    async def _finalize_proposal(self, prop: GovernanceProposal):
        """Applies the proposal once consensus is reached."""
        logger.info(f"🏆 [Governance] Proposal {prop.proposal_id} passed! Finalizing...")
        
        if prop.proposal_type == "model_upgrade":
            # Logic to update ModelRouter or pull new weights
            logger.info(f"🚀 [Upgrade] Model graduated to {prop.payload.get('version')}")
             # We would broadcast a Raft pulse here to ensure all nodes apply it
            await self.dcn.broadcast_mission_truth(
                mission_id=f"finalize_{prop.proposal_id}",
                outcome={"status": "graduated", "version": prop.payload.get("version")}
            )
            
        del self.active_proposals[prop.proposal_id]

governance_engine = GovernanceEngine()
