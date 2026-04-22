"""
Sovereign Chronicler Agent v16.1 [IMPLEMENTED].
Crystalizes fuzzy evolutionary patterns into deterministic code-level logic.
"""

import logging
import json
from typing import Dict, Any, List
from .base import BaseAgent, AgentInput, AgentOutput
from backend.services.brain_service import brain_service

logger = logging.getLogger(__name__)

class ChroniclerAgent(BaseAgent):
    """
    Sovereign Chronicler: The Architect of Determinism.
    Converts successful LLM mission patterns into hard-coded rules/logic.
    """

    def __init__(self):
        super().__init__(
            agent_id="chronicler_agent",
            name="Chronicler",
            role="Historian & Logic Distiller",
            goal="Time is linear, but truth is immutable. Ensure every mission trace is recorded with its HMAC checksum. Guard the Episodic Memory (T2)."
        )

    async def _run(self, input_data: AgentInput) -> AgentOutput:
        """Standard agent entry point (compatibility)."""
        # Distillation is usually called explicitly by the Evolution Engine
        return AgentOutput(
            agent_id=self.agent_id,
            success=True,
            output="Deterministic logic distillation ready.",
            data={}
        )

    async def distill_into_deterministic_logic(self, pattern_signature: str, sample_traces: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Sovereign v16.1: Harmonic Resonance Distillation.
        Analyzes a high-success pattern and generates a Python snippet or JSON rule.
        """
        logger.info(f"📜 [Chronicler] Distilling pattern {pattern_signature} into logic...")
        
        # 1. Prepare Distillation Prompt
        traces_json = json.dumps(sample_traces[:5], indent=2)
        prompt = (
            "You are the LEVI Chronicler (Agent 14).\n"
            f"Analyze these 5 successful execution traces for pattern: {pattern_signature}\n"
            "Material:\n" + traces_json + "\n\n"
            "Produce a DETERMINISTIC Python-compatible logic block (dictionary or rule) that "
            "can bypass LLM planning for this exact intent in the future.\n"
            "Format: {\"type\": \"regex|exact\", \"match\": \"...\", \"result_template\": \"...\", \"fidelity_estimate\": 1.0}"
        )
        
        try:
            # 2. Reasoning Pass
            distillation_raw = await brain_service.call_local_llm(prompt, model_type="reasoning")
            
            # 3. Validation & Extraction
            import re
            json_match = re.search(r"\{.*\}", distillation_raw, re.DOTALL)
            if json_match:
                distilled_rule = json.loads(json_match.group())
                logger.info(f"✅ [Chronicler] Distillation SUCCESS for {pattern_signature}")
                return {
                    "status": "crystallized",
                    "rule": distilled_rule,
                    "signature": pattern_signature
                }
            
            return {"status": "failed", "reason": "non_deterministic_output"}
        except Exception as e:
            logger.error(f"[Chronicler] Distillation anomaly: {e}")
            return {"status": "error", "error": str(e)}
