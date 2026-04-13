"""
Sovereign Perception Layer v14.0.
Extracts intent, entities, and compresses user input into an Intent Graph.
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List

from .intent_classifier import HybridIntentClassifier
from .orchestrator_types import IntentResult, IntentGraph, IntentNode, IntentEdge
from backend.auth.models import UserProfile as UserIdentity
from backend.core.memory_manager import MemoryManager
from backend.utils.audit import AuditLogger
from backend.utils.shield import SovereignShield


logger = logging.getLogger(__name__)

class PerceptionEngine:
    """
    v15.0 Perception Layer.
    Implements Intent Compression, Context Hydration, and Hybrid Classification.
    """
    def __init__(self, memory: MemoryManager):
        self.memory = memory
        self.classifier = HybridIntentClassifier()

    async def perceive(self, user_input: str, user_id: str, session_id: str, **kwargs) -> Dict[str, Any]:
        """
        Synthesizes raw input into a structured cognitive perception.
        Performs Intent Compression (User Query -> Intent Graph).
        """
        # 0. Sovereign Shield: PII Masking
        safe_input = SovereignShield.mask_pii(user_input)
        
        # 1. Hybrid Intent Analysis (v15.0 Hardened)
        intent = await self.classifier.classify(safe_input)

        # 2. INTENT COMPRESSION (v14.0 Upgrade)
        intent_graph = self._compress_intent(safe_input, intent)
        
        # 3. Context Hydration (4-Tier Memory)
        # Hydrate with full unified context (Vector + Graph + Interaction Pulse)
        context = await self.memory.get_unified_context(user_id, session_id, safe_input)
        context.update(kwargs)
        
        return {
            "input": safe_input,
            "raw_input": user_input,
            "intent": intent,
            "intent_graph": intent_graph,
            "context": context,
            "user_id": user_id,
            "session_id": session_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    def _compress_intent(self, text: str, intent: IntentResult) -> IntentGraph:
        """
        Intent Compression: Structured representation of user intent.
        """
        nodes = []
        edges = []
        
        # Root Intent Node
        root_id = f"intent_{uuid.uuid4().hex[:4]}"
        nodes.append(IntentNode(
            id=root_id,
            label=intent.intent_type,
            confidence=intent.confidence_score
        ))
        
        # Extract keywords/entities (Simplified for v14.0 base)
        words = text.split()
        if len(words) > 0:
            for i, word in enumerate(words[:5]): # Capture key tokens as entities
                if len(word) > 3:
                    entity_id = f"ent_{uuid.uuid4().hex[:4]}"
                    nodes.append(IntentNode(id=entity_id, label="entity", entity=word))
                    edges.append(IntentEdge(source=root_id, target=entity_id, relation="references"))

        return IntentGraph(
            nodes=nodes,
            edges=edges,
            metadata={
                "complexity": intent.complexity_level,
                "cost_weight": intent.estimated_cost_weight
            }
        )
