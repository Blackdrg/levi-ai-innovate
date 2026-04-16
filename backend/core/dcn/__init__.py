"""
backend/core/dcn — Distributed Cognitive Network Package

Exports:
    RaftConsensus  — Redis-backed Raft-lite consensus engine.
    DCNMesh        — High-level facade for distributed mission decisions.
    DCNGossip      — Gossip-based state sync.
    ConsistencyEngine — Anti-entropy reconciliation.
    get_raft_consensus / get_dcn_mesh — singleton accessors.
"""

from .raft_consensus import RaftConsensus, DCNMesh, get_raft_consensus, get_dcn_mesh
from .gossip import DCNGossip, GossipProtocol
from .consistency import ConsistencyEngine

__all__ = [
    "RaftConsensus",
    "DCNMesh",
    "get_raft_consensus",
    "get_dcn_mesh",
    "DCNGossip",
    "GossipProtocol",
    "ConsistencyEngine",
]
