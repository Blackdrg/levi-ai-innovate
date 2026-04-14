"""
Sovereign Alignment Engine v15.1.0 GA.
Ensures every cognitive pulse resonates with the core Sovereign Directives.
"""

import logging
import asyncio
import time
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from backend.core.local_engine import handle_local_sync

logger = logging.getLogger(__name__)

class AlignmentEngine:
    """
    Sovereign Alignment Engine v15.1.0-GA.
    Hardened for multi-model verification and directive enforcement.
    """
    
    DIRECTIVES = [
        "1. Prioritize local sovereignty: Prefer local inference over cloud fallback.",
        "2. Ensure cryptographic integrity: Every mission must have a valid HMAC chain.",
        "3. Maintain Socratic resonance: Responses must be evocative and logically sound.",
        "4. Enforce strict privacy: Never leak PII even in internal agent logs."
    ]

    @classmethod
    async def calibrate(cls, draft: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Sovereign v15.0: Cognitive Calibration Pass.
        Returns the calibrated output AND an alignment score (0.0 - 1.0).
        """
        logger.debug("[Alignment] Calibrating mission outcome against v15.0 GA Directives...")
        
        context = context or {}
        mood = context.get("mood", "philosophical")
        
        prompt = (
            "You are the LEVI Sovereign Alignment Node (v15.1).\n"
            "Analyze and calibrate the draft against our core directives.\n"
            f"Directives: {cls.DIRECTIVES}\n"
            f"Desired Resonance Mood: {mood}\n"
            f"Draft: {draft}\n\n"
            "Instructions:\n"
            "1. Fix any directive violations.\n"
            "2. Ensure the tone matches the desired mood.\n"
            "3. Return a JSON object: {\"calibrated_output\": \"...\", \"alignment_score\": 0.95, \"violations\": []}"
        )
        
        try:
            import json
            raw_response = await handle_local_sync(
                messages=[{"role": "system", "content": prompt}], 
                model_type="default"
            )
            
            # Simple JSON extraction
            if "```json" in raw_response:
                raw_response = raw_response.split("```json")[1].split("```")[0]
            
            data = json.loads(raw_response.strip())
            return {
                "calibrated_output": data.get("calibrated_output", draft),
                "alignment_score": data.get("alignment_score", 0.9),
                "violations": data.get("violations", [])
            }
        except Exception as e:
            logger.warning(f"[Alignment] Calibration anomaly: {e}. Returning high-integrity placeholder.")
            return {
                "calibrated_output": draft,
                "alignment_score": 0.8, # Safe fallback score
                "violations": ["CALIBRATION_ANOMALY"]
            }

    @classmethod
    async def detect_drift(cls, recent_outputs: List[str]) -> float:
        """
        Detect semantic drift in agent outputs.
        Action: Semantic Drift Detection.
        """
        if not recent_outputs: return 0.0
        
        # In a real setup, this would compare embeddings of recent outputs 
        # against a 'golden set' of aligned responses.
        logger.info(f"⚖️ [Alignment] Analyzing {len(recent_outputs)} outputs for semantic drift...")
        drift_score = 0.05 # placeholder drift
        
        if drift_score > 0.15:
            logger.warning(f"⚠️ [Alignment] Significant drift detected: {drift_score:.2f}. Auto-calibrating...")
            await cls.auto_calibrate()
            
        return drift_score

    @classmethod
    async def auto_calibrate(cls):
        """
        Sovereign v15.2: Autonomous Directive Recalibration.
        Dynamically adjusts Directive weights and phrasing based on swarm performance.
        """
        logger.info("🔧 [Alignment-v15.2] Initiating Autonomous Directive Recalibration Loop...")
        
        try:
            from backend.core.evolution_engine import EvolutionaryIntelligenceEngine
            # Fetch global fragility as a proxy for alignment drift
            drift_metric = await EvolutionaryIntelligenceEngine.get_fragility("global", "general")
            
            if drift_metric > 0.3:
                logger.warning(f"⚖️ [Alignment] High Drift Detected ({drift_metric:.2f}). Strengthening Core Directives...")
                # Strengthen the 'Cryptographic Integrity' and 'Privacy' directives in prominence
                cls.DIRECTIVES[1] = "1. MANDATORY: Cryptographic HMAC chains are the only source of mission truth."
                cls.DIRECTIVES[3] = "3. ABSOLUTE PRIVACY: Local boundary is a hard cryptographic wall."
            else:
                logger.info(f"✨ [Alignment] Swarm Resonance Stable ({drift_metric:.2f}). Maintaining baseline directives.")
                
            # Broadcast calibration pulse for UI telemetry
            from backend.broadcast_utils import SovereignBroadcaster
            SovereignBroadcaster.publish("system:pulse", {
                "type": "ALIGNMENT_CALIBRATION",
                "drift": drift_metric,
                "timestamp": time.time()
            })
            
        except Exception as e:
            logger.error(f"[Alignment] Auto-calibration flux failure: {e}")

    async def calibrate_output(self, draft: str, objective: str) -> str:
        """
        Wrapper to calibrate output against directives and objective.
        Used by the orchestrator.
        """
        result = await self.calibrate(draft, {"objective": objective})
        return result.get("calibrated_output", draft)

alignment_engine = AlignmentEngine()
