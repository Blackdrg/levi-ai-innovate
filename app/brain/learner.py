import json, logging
from backend.utils.llm_utils import call_lightweight_llm

logger = logging.getLogger(__name__)

class CognitiveLearner:
    """
    Sovereign v13: Autonomous Cognitive Refinement.
    Learns from mission fidelity and evolves instructions.
    """
    @staticmethod
    async def score_mission(results: dict, prompt: str) -> float:
        """Critic: Scores the fidelity of the results against the original prompt."""
        critic_prompt = f"""
        Rate the results of this mission from 0.0 to 1.0 based on fidelity to the prompt.
        Prompt: {prompt}
        Results: {json.dumps(results)}
        Output ONLY a number.
        """
        try:
            score_str = await call_lightweight_llm([{"role": "system", "content": critic_prompt}])
            return float(score_str.strip())
        except Exception as e:
            logger.error(f"Critic failure: {e}")
            return 0.5

    @staticmethod
    async def refine_instructions(failure_report: str):
        """Evolver: Mutates system prompts to avoid future fidelity gaps."""
        # This would typically update a 'seed' doc in Postgres or local cache
        logger.info(f"Refining cognitive instruction based on: {failure_report[:50]}")
        pass
