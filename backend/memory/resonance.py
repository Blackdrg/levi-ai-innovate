"""
Sovereign Memory Resonance v8.
Calculates survival scores (decay) and manages evolutionary distillation of core traits.
"""

import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from backend.db.firestore_db import db as firestore_db

logger = logging.getLogger(__name__)

class MemoryResonance:
    """
    LeviBrain v8: Resonance Engine.
    Handles the psychological depth and evolutionary life-of-data.
    """

    @staticmethod
    def apply_decay(facts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Calculates a 'survival_score' based on importance and recency.
        Higher importance or recency = higher survival score.
        """
        now = datetime.now(timezone.utc)
        decayed_facts = []
        
        for f in facts:
            try:
                # Use isoformat to parse the creation timestamp
                created_at_str = f.get("created_at")
                if created_at_str:
                    created_at = datetime.fromisoformat(created_at_str)
                    age_days = (now - created_at).days
                    # Recency factor: decays over 90 days
                    recency_factor = max(0, (90 - age_days) / 90)
                else:
                    recency_factor = 0.5
                
                importance = f.get("importance", 0.5)
                # Survival = (Importance * 0.7) + (Recency * 0.3)
                survival_score = (importance * 0.7) + (recency_factor * 0.3)
                
                # Keep if survival is high enough or it's a core trait
                if survival_score > 0.3 or importance > 0.8:
                    f["survival_score"] = survival_score
                    decayed_facts.append(f)
            except Exception as e:
                logger.warning(f"Resonance decay anomaly: {e}")
                decayed_facts.append(f)
                
        return sorted(decayed_facts, key=lambda x: x.get("survival_score", 0), reverse=True)

    @staticmethod
    async def distill_traits(user_id: str, relevant_facts: List[Any]) -> List[Dict[str, Any]]:
        """
        Analyzes fragmented clusters of facts and distills them into permanent core traits.
        (Called periodicially by the Memory Manager)
        """
        from backend.core.planner import call_lightweight_llm
        import json

        if len(relevant_facts) < 10:
            return [] # Not enough material for high-fidelity distillation

        fact_strings = "\n".join([f"- {f.get('fact')} (Importance: {f.get('importance', 0.5)})" for f in relevant_facts])
        
        prompt = (
            "You are the LEVI Core Distiller. Analyze these fragmented user facts and distill them into "
            "3-5 deep, high-level core identity traits or permanent preferences.\n"
            f"Facts:\n{fact_strings}\n\n"
            "Output ONLY JSON: {\"distilled_traits\": [{\"fact\": \"...\", \"importance\": 0.95}]}"
        )

        try:
            raw_json = await call_lightweight_llm([{"role": "system", "content": prompt}])
            if "```json" in raw_json: raw_json = raw_json.split("```json")[1].split("```")[0]
            
            data = json.loads(raw_json.strip())
            return data.get("distilled_traits", [])
        except Exception as e:
            logger.error(f"Resonance distillation failure for {user_id}: {e}")
            return []
