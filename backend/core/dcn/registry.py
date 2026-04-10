from typing import Optional
from .gossip import DCNGossip
from .consistency import ConsistencyEngine
import os

class DCNRegistry:
    _gossip: Optional[DCNGossip] = None
    _consistency: Optional[ConsistencyEngine] = None

    @classmethod
    def get_gossip(cls) -> DCNGossip:
        if cls._gossip is None:
            cls._gossip = DCNGossip()
        return cls._gossip

    @classmethod
    def get_consistency(cls) -> ConsistencyEngine:
        if cls._consistency is None:
            node_id = os.getenv("DCN_NODE_ID", "node-alpha")
            cls._consistency = ConsistencyEngine(node_id=node_id)
        return cls._consistency

dcn_registry = DCNRegistry()
