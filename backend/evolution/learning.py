from typing import Dict, Any, List, Optional
import asyncio
from datetime import datetime, timezone

class SuccessPatternLearner:
    """
    Sovereign Continuous Learning System (Weeks 29-32).
    Extracts successful patterns from high-fidelity missions.
    """
    
    def __init__(self):
        self.pattern_store = {} # In-memory cache of success patterns

    async def analyze_success(self, mission_id: str, results: Dict[str, Any], performance: Dict[str, Any]):
        """Analyze a successful mission and persist the strategy pattern."""
        fidelity = performance.get("accuracy", 0.0)
        
        if fidelity > 0.90:
            objective = results.get("objective", "")
            if not objective: return
            
            agent_sequence = results.get("agent_sequence", [])
            parameters = results.get("parameters", {})
            
            # Persist to database
            try:
                from backend.db.models import SuccessPattern
                from backend.db.postgres import PostgresDB
                from sqlalchemy import select
                
                async with PostgresDB._session_factory() as session:
                    # Check if pattern exists (using text similarity or exact match)
                    stmt = select(SuccessPattern).where(SuccessPattern.objective_pattern == objective)
                    result = await session.execute(stmt)
                    existing = result.scalar_one_or_none()
                    
                    if existing:
                        # Update running average fidelity and count
                        total_fidelity = (existing.fidelity_avg * existing.win_count) + fidelity
                        existing.win_count += 1
                        existing.fidelity_avg = total_fidelity / existing.win_count
                        existing.last_used_at = datetime.now(timezone.utc)
                    else:
                        new_pattern = SuccessPattern(
                            objective_pattern=objective,
                            agent_sequence=agent_sequence,
                            parameters=parameters,
                            fidelity_avg=fidelity,
                            win_count=1
                        )
                        session.add(new_pattern)
                    
                    await session.commit()
                    print(f"📖 Learned success pattern for objective: {objective[:50]}...")
            except Exception as e:
                print(f"❌ Failed to persist success pattern: {e}")

            # Also update in-memory cache
            self.pattern_store[objective] = {
                "agent_sequence": agent_sequence,
                "parameters": parameters,
                "fidelity": fidelity
            }

    async def get_suggested_strategy(self, objective: str) -> Optional[Dict[str, Any]]:
        """Retrieve a proven strategy from DB or cache."""
        # 1. Check local cache
        if objective in self.pattern_store:
            return self.pattern_store[objective]
            
        # 2. Check Database
        try:
            from backend.db.models import SuccessPattern
            from backend.db.postgres import PostgresDB
            from sqlalchemy import select
            
            async with PostgresDB._session_factory() as session:
                stmt = select(SuccessPattern).where(SuccessPattern.objective_pattern == objective)
                result = await session.execute(stmt)
                pattern = result.scalar_one_or_none()
                if pattern:
                    return {
                        "agent_sequence": pattern.agent_sequence,
                        "parameters": pattern.parameters,
                        "fidelity_avg": pattern.fidelity_avg
                    }
        except Exception as e:
            print(f"⚠️ Failed to query success patterns: {e}")
            
        return None

# Global singleton
learner = SuccessPatternLearner()
