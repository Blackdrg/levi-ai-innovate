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
        LeviBrain v9.8: Resonance Survival Formula.
        Calculates a 'survival_score' based on importance, recency, and Frequency of Access (F.O.A).
        """
        now = datetime.now(timezone.utc)
        decayed_facts = []
        
        for f in facts:
            try:
                # 1. Recency Factor (90-day linear decay)
                created_at_str = f.get("created_at")
                if created_at_str:
                    created_at = datetime.fromisoformat(created_at_str)
                    age_days = (now - created_at).days
                    recency_factor = max(0, (90 - age_days) / 90)
                else:
                    recency_factor = 0.5
                
                # 2. Importance (Core weight)
                importance = f.get("importance", 0.5)
                
                # 3. Frequency of Access (v9.8 Neural Resonance)
                access_count = f.get("access_count", 1)
                access_factor = min(1.0, access_count / 15)
                
                # Survival Formula: Importance (50%) + Access (30%) + Recency (20%)
                survival_score = (importance * 0.5) + (access_factor * 0.3) + (recency_factor * 0.2)
                
                # Keep if survival is high enough or it's a critical core trait
                if survival_score > 0.35 or importance > 0.85:
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
