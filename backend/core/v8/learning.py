import logging
import asyncio
import json
from datetime import datetime, timezone
from typing import Dict, Any, List
from ...kafka_client import LeviKafkaClient

logger = logging.getLogger(__name__)

class LearningLoopV8:
    """
    LeviBrain v8: Autonomous Learning Loop
    Feedback pipeline and Failure clustering via Kafka events.
    """

    @classmethod
    @classmethod
    async def process_feedback(cls, event: Dict[str, Any]):
        """
        LeviBrain v8: High-Fidelity Feedback Processor.
        Vectorizes successful missions into shared traits.
        """
        rating = event.get("rating", 0)
        fidelity = event.get("fidelity", 0.0)
        
        if rating >= 4 or fidelity >= 0.9:
            logger.info("[V8 Learning] High-fidelity mission detected. Distilling trait...")
            await cls.distill_trait(event)
        elif rating <= 2 or fidelity < 0.7:
            logger.warning("[V8 Learning] Mission divergence. Archiving failure graph for clustering.")
            await LeviKafkaClient.send_event("mission.failures", {
                **event,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "node_failures": [n for n in event.get("nodes", []) if not n.success]
            })

    @classmethod
    async def distill_trait(cls, event: Dict[str, Any]):
        """
        Extracts successful reasoning patterns and commits them to the Semantic Vault.
        This enables 'Autonomous Skill Acquisition'.
        """
        trait_id = f"trait_{uuid.uuid4().hex[:8]}"
        summary = event.get("summary", "N/A")
        
        trait_data = {
            "id": trait_id,
            "pattern": event.get("methodology", "N/A"),
            "context": event.get("input", ""),
            "success_metrics": event.get("metrics", {}),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        logger.info("[V8 Learning] Trait distiled: %s", trait_id)
        # In production, this would be a vector storage call
        await LeviKafkaClient.send_event("intelligence.traits", trait_data)

    @classmethod
    async def apply_importance_decay(cls, memory_vault: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        v8 Heuristic: Purges low-resonance/obsolete memories.
        Maintains a 'Lean Cognitive State'.
        """
        now = datetime.now(timezone.utc)
        survivors = []
        
        for mem in memory_vault:
            # Resonance = Importance / Age
            age_days = (now - datetime.fromisoformat(mem["timestamp"])).days
            importance = mem.get("importance", 5)
            resonance = importance / (1 + age_days * 0.1)
            
            if resonance > 0.5:
                survivors.append(mem)
            else:
                logger.debug("[V8 Learning] Memory decayed: %s", mem.get("id"))
                
        return survivors
