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
    def calculate_resonance(importance: float, created_at: Optional[datetime], access_count: int = 1, success_impact: float = 0.5) -> float:
        """
        Primary Resonance Formula v11.0:
        R = (importance * 0.4) + (recency * 0.2) + (usage_frequency * 0.2) + (success_impact * 0.2)
        """
        now = datetime.now(timezone.utc)
        
        # 1. Recency Calculation (0.0 to 1.0)
        if not created_at:
            recency = 0.5
        else:
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=timezone.utc)
            age_days = max(0, (now - created_at).days)
            recency = 1.0 / (1.0 + (age_days * 0.05)) # Decay over 20 days to 0.5
            
        # 2. Usage Frequency (0.0 to 1.0)
        # Normalize access count, assuming 20 hits is 'high frequency'
        usage_frequency = min(1.0, access_count / 20.0)
        
        # 3. 4-Factor Weighted Calculation
        resonance = (
            (importance * 0.4) + 
            (recency * 0.2) + 
            (usage_frequency * 0.2) + 
            (success_impact * 0.2)
        )
        
        return round(resonance, 4)

    @staticmethod
    def apply_decay(facts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        LeviBrain v9.8.1: Resonance Survival Filter.
        Calculates survival scores and filters out memories below threshold.
        """
        decayed_facts = []
        SURVIVAL_THRESHOLD = 0.35 # Standard v9.8 Threshold
        
        for f in facts:
            try:
                importance = f.get("importance", 0.5)
                created_at_str = f.get("created_at")
                access_count = f.get("access_count", 1)
                success_impact = f.get("success_impact", 0.5)
                
                created_at = None
                if created_at_str:
                    try:
                        created_at = datetime.fromisoformat(str(created_at_str).replace('Z', '+00:00'))
                    except Exception:
                        created_at = None
                
                resonance = MemoryResonance.calculate_resonance(importance, created_at, access_count, success_impact)
                f["survival_score"] = resonance
                
                # Persistence Logic: Keep if resonant or high-importance
                if resonance >= SURVIVAL_THRESHOLD or importance >= 0.9:
                    decayed_facts.append(f)
                    
            except Exception as e:
                logger.warning(f"Resonance decay anomaly: {e}")
                f["survival_score"] = f.get("importance", 0.5)
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
