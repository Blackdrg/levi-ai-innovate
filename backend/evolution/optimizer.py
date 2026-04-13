from typing import Dict, Any, List
import asyncio
import random

class ParameterOptimizer:
    """
    Sovereign Automated Parameter Tuning (Weeks 29-32).
    Optimizes system hyperparameters using A/B testing.
    """
    
    def __init__(self):
        self.current_params = {
            "bert_confidence_threshold": 0.65,
            "max_parallel_agents": 4,
            "agent_timeout": 60,
            "retry_count": 3,
            "temperature": 0.7
        }
        self.experiments = {}

    async def get_parameters(self, mission_id: str) -> Dict[str, Any]:
        """Return parameters, potentially applying an experiment variation."""
        # Simple A/B test logic: 20% of missions get a variation
        if random.random() < 0.2:
            variation = self.generate_variation()
            self.experiments[mission_id] = variation
            return variation
            
        return self.current_params

    def generate_variation(self) -> Dict[str, Any]:
        """Create a randomized variation of current parameters."""
        variation = self.current_params.copy()
        # Randomly nudge one parameter
        param_to_nudge = random.choice(list(variation.keys()))
        if isinstance(variation[param_to_nudge], float):
            variation[param_to_nudge] += random.uniform(-0.05, 0.05)
        elif isinstance(variation[param_to_nudge], int):
            variation[param_to_nudge] += random.choice([-1, 1])
            
        # Ensure bounds
        variation["temperature"] = max(0.0, min(1.0, variation["temperature"]))
        variation["max_parallel_agents"] = max(1, min(10, variation["max_parallel_agents"]))
        
        return variation

    async def report_result(self, mission_id: str, success_score: float):
        """Update optimizer with result of a mission and adopt improvements."""
        if mission_id in self.experiments:
            variation = self.experiments[mission_id]
            
            # Simple hill-climbing: If success score is high, potentially adopt variation
            if success_score > 0.95:
                # In a real system, we'd average over multiple runs
                # Here we'll log it as a successful mutation proposal
                try:
                    from backend.db.models import MutationProposal
                    from backend.db.postgres import PostgresDB
                    
                    async with PostgresDB._session_factory() as session:
                        proposal = MutationProposal(
                            mutation_type="parameter_tuning",
                            proposal_name=f"Opt-{mission_id[:8]}",
                            logic_diff=f"Updated parameters: {variation}",
                            target_metric="accuracy",
                            expected_improvement=success_score - 0.90, # Relative to baseline
                            status="adopted" if success_score > 0.98 else "testing"
                        )
                        session.add(proposal)
                        
                        # Slowly adopt the best parameters
                        if success_score > 0.98:
                            for k, v in variation.items():
                                # Weighted average update (exponential moving average)
                                self.current_params[k] = (self.current_params[k] * 0.9) + (v * 0.1)
                            print(f"📈 Parameters optimized and adopted after mission {mission_id}")
                        
                        await session.commit()
                except Exception as e:
                    print(f"❌ Failed to persist optimizer proposal: {e}")
            
            del self.experiments[mission_id]

# Global singleton
optimizer = ParameterOptimizer()
