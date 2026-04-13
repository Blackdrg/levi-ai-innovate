from typing import Dict, Any, List, Optional
import json
from datetime import datetime, timezone

class FailureAnalyzer:
    """
    Sovereign Failure Analysis Engine (Weeks 25-28).
    Analyzes why missions fail and generates fix suggestions.
    """
    
    async def analyze_failure(self, mission_id: str, error_trace: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Categorize failure, extract root cause, and persist pattern."""
        
        failure_type = self.categorize_error(error_trace)
        root_cause = self.extract_root_cause(error_trace, context)
        fix_suggestion = self.generate_fix_suggestion(failure_type, root_cause)
        
        analysis = {
            "mission_id": mission_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "failure_type": failure_type,
            "root_cause": root_cause,
            "fix_suggestion": fix_suggestion,
            "is_critical": self.is_critical(failure_type)
        }
        
        # Persist to database
        try:
            from backend.db.models import FailurePattern
            from backend.db.postgres import PostgresDB
            from sqlalchemy import select, update
            
            async with PostgresDB._session_factory() as session:
                # Check if pattern exists
                stmt = select(FailurePattern).where(FailurePattern.failure_type == failure_type)
                result = await session.execute(stmt)
                existing_pattern = result.scalar_one_or_none()
                
                if existing_pattern:
                    existing_pattern.occurrence_count += 1
                    existing_pattern.last_seen_at = datetime.now(timezone.utc)
                    existing_pattern.root_cause = root_cause # Update with latest context
                else:
                    new_pattern = FailurePattern(
                        failure_type=failure_type,
                        root_cause=root_cause,
                        fix_suggestion=fix_suggestion,
                        occurrence_count=1
                    )
                    session.add(new_pattern)
                
                await session.commit()
                print(f"🕵️ Failure pattern '{failure_type}' analyzed and persisted.")
        except Exception as e:
            print(f"❌ Failed to persist failure pattern: {e}")

        return analysis

    def categorize_error(self, error_trace: str) -> str:
        """Heuristic-based error categorization."""
        error_trace = error_trace.lower()
        if "timeout" in error_trace:
            return "agent_timeout"
        if "rate limit" in error_trace or "429" in error_trace:
            return "external_api_rate_limit"
        if "hallucination" in error_trace or "fact check failed" in error_trace:
            return "hallucination_detected"
        if "memory" in error_trace or "vram" in error_trace:
            return "resource_exhaustion"
        if "validation" in error_trace:
            return "output_validation_failure"
        return "unknown_reasoning_failure"

    def extract_root_cause(self, error_trace: str, context: Dict[str, Any]) -> str:
        """Extract the specific agent or component that failed."""
        # Logic to parse the trace and find the culprit agent
        culprit = context.get("failed_agent", "unknown_orchestrator")
        return f"Failure in component: {culprit}. Details: {error_trace[:200]}..."

    def generate_fix_suggestion(self, failure_type: str, root_cause: str) -> str:
        """AI-assisted suggestions for recovery."""
        fixes = {
            "agent_timeout": "Increase agent_timeout parameter or optimize search depth.",
            "external_api_rate_limit": "Switch to fallback provider or implement jittered retries.",
            "hallucination_detected": "Add CriticalValidator agent to the next wave or decrease temperature.",
            "resource_exhaustion": "Enable memory swapping or reduce parallel agent count.",
            "output_validation_failure": "Refine output JSON schema or provide more explicit few-shot examples."
        }
        return fixes.get(failure_type, "Run deep reasoning diagnostics on the failing agent chain.")

    def is_critical(self, failure_type: str) -> bool:
        """Determine if system-wide action is needed."""
        return failure_type in ["resource_exhaustion", "external_api_rate_limit"]

# Global singleton
analyzer = FailureAnalyzer()
