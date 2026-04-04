import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class LLMGuard:
    """
    LeviBrain v8.12: LLM Gatekeeper.
    Enforces Brain authority by blocking LLM calls for deterministic or memory-matched tasks.
    """

    @staticmethod
    def allow_llm(task_description: str, decision_data: Dict[str, Any]) -> bool:
        """
        Decision Logic:
        - IF internal_confidence >= 0.7: -> BLOCK LLM (Internal Match)
        - ELSE IF engine_capable == true: -> BLOCK LLM (Engine Move)
        - ELSE IF memory_match_score >= 0.7: -> BLOCK LLM (Direct Memory)
        - ELSE: -> ALLOW LLM (Neural Fallback)
        """
        internal_conf = decision_data.get("internal_conf", 0)
        engine_capable = decision_data.get("engine_capable", False)
        memory_match = decision_data.get("memory_match", 0)

        if internal_conf >= 0.7:
             logger.info(f"[LLMGuard] Blocking LLM: Internal Match High ({internal_conf}).")
             return False
             
        if engine_capable:
             logger.info(f"[LLMGuard] Blocking LLM: Engine Capability Detected.")
             return False

        if memory_match >= 0.7:
             logger.info(f"[LLMGuard] Blocking LLM: Direct Memory Match ({memory_match}).")
             return False

        logger.info(f"[LLMGuard] Allowing LLM: Neural Fallback required.")
        return True
