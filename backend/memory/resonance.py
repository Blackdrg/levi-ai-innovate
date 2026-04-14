"""
Sovereign Memory Resonance v15.0-GA.
Calculates survival scores (decay) and manages autonomous evolutionary distillation of traits.
"""

import logging
import json
import asyncio
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class MemoryResonance:
    """
    Sovereign Resonance Engine v15.0-GA.
    Handles the psychological depth and evolutionary life-of-data.
    """

    @staticmethod
    def calculate_resonance(importance: float, created_at: Optional[datetime], access_count: int = 1, success_impact: float = 0.5) -> float:
        """
        Sovereign v15.0 4-Factor Resonance Formula:
        R = (Importance * 0.45) + (Recency * 0.20) + (Usage * 0.20) + (SuccessImpact * 0.15)
        """
        now = datetime.now(timezone.utc)
        
        # 1. Sigmoid Recency Calculation (0.0 to 1.0)
        if not created_at:
            recency = 0.5
        else:
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=timezone.utc)
            age_hours = max(0, (now - created_at).total_seconds() / 3600.0)
            # Half-life of 240 hours (10 days)
            recency = 1.0 / (1.0 + (age_hours / 240.0))
            
        # 2. Logistic Usage Frequency (0.0 to 1.0)
        # Normalize access count: 5 hits = 0.5, 20 hits = 1.0
        usage_frequency = min(1.0, access_count / 20.0)
        
        # 3. 4-Factor Weighted Calculation
        resonance = (
            (importance * 0.45) + 
            (recency * 0.20) + 
            (usage_frequency * 0.20) + 
            (success_impact * 0.15)
        )
        
        return round(resonance, 4)

    @classmethod
    def apply_decay(cls, facts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Sovereign v15.0: Resonance Survival Filter.
        Applies non-linear decay and prunes low-resonance noise.
        """
        decayed_facts = []
        # GA Threshold: Memories with <0.30 resonance are archived (removed from active pool)
        SURVIVAL_THRESHOLD = 0.30 
        
        for f in facts:
            try:
                importance = f.get("importance", 0.5)
                # Handle varying date formats
                created_at_val = f.get("created_at")
                access_count = f.get("access_count", 1)
                success_impact = f.get("success_impact", 0.5)
                
                created_at = None
                if isinstance(created_at_val, datetime):
                    created_at = created_at_val
                elif created_at_val:
                    try:
                        created_at = datetime.fromisoformat(str(created_at_val).replace('Z', '+00:00'))
                    except Exception:
                        created_at = None
                
                resonance = cls.calculate_resonance(importance, created_at, access_count, success_impact)
                f["survival_score"] = resonance
                
                # Persistence Logic: Keep if resonant or critical (high-importance)
                if resonance >= SURVIVAL_THRESHOLD or importance >= 0.85:
                    decayed_facts.append(f)
                else:
                    logger.debug(f"[Resonance] Pruning faded memory: {f.get('fact', '')[:30]}... (Score: {resonance})")
                    
            except Exception as e:
                logger.warning(f"[Resonance] Decay anomaly: {e}")
                f["survival_score"] = f.get("importance", 0.5)
                decayed_facts.append(f)
                
        return sorted(decayed_facts, key=lambda x: x.get("survival_score", 0), reverse=True)

    @staticmethod
    async def distill_traits(user_id: str, relevant_facts: List[Any]) -> List[Dict[str, Any]]:
        """
        Sovereign v15.0: Autonomous Identity Crystallization.
        Distills fragmented episodic clusters into high-level permanent persona traits.
        """
        from backend.core.planner import call_lightweight_llm

        if len(relevant_facts) < 8:
            return [] # Insufficient density for high-fidelity crystallization

        fact_strings = "\n".join([f"- {f.get('fact')} (Score: {f.get('survival_score', 0.5)})" for f in relevant_facts])
        
        prompt = f"""
[Sovereign Identity Distiller v15]
Analyze these {len(relevant_facts)} high-resonance facts about User {user_id}.
Distill them into a focused set of 3-5 high-level core identity traits or persistent preferences.
Ensure these traits are actionable for downstream prompt engineering.

Facts:
{fact_strings}

Output ONLY valid JSON representing the distilled model:
{{
  "user_id": "{user_id}",
  "distilled_traits": [
    {{
      "fact": "High-level trait description",
      "importance": 0.95,
      "category": "trait",
      "resonance_source_count": 5
    }}
  ]
}}
"""
        try:
            raw_json = await call_lightweight_llm([{"role": "system", "content": prompt}])
            if "```json" in raw_json: raw_json = raw_json.split("```json")[1].split("```")[0]
            
            data = json.loads(raw_json.strip())
            traits = data.get("distilled_traits", [])
            
            # 🔗 [Wire] Register Crystallization with MCM for Swarm Synchronization
            if traits:
                try:
                    from backend.memory.consistency import MemoryConsistencyManager
                    # Registering as a 'profile_update' event to trigger cluster-wide sync
                    MemoryConsistencyManager.register_event(
                        user_id=user_id,
                        payload={
                            "type": "profile_update",
                            "traits": traits,
                            "source": "CognitiveDistillationV15"
                        },
                        broadcast=True
                    )
                    logger.info(f"✨ [Resonance] Crystallized {len(traits)} traits for {user_id} and broadcast to swarm.")
                except Exception as e:
                    logger.error(f"[Resonance] Swarm registration fail: {e}")

            return traits
        except Exception as e:
            logger.error(f"[Resonance] Distillation failure for {user_id}: {e}")
            return []
