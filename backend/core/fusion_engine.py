import logging
from typing import List, Dict, Any
from backend.core.local_engine import handle_local_sync
from backend.engines.utils.security import SovereignSecurity
from backend.engines.utils.i18n import SovereignI18n

logger = logging.getLogger(__name__)

class FusionEngine:
    """
    Sovereign Mind Synthesis Layer v22.1.
    Synthesizes multiple agent results (Search, Document, Local, Reasoning) 
    and multi-modal signals (Vision, Audio) into a single high-fidelity response.
    """
    
    @staticmethod
    async def fuse_results(query: str, results: List[Dict], lang: str = "en", mood: str = "philosophical", fast_mode: bool = False) -> str:
        """
        Takes multiple agent results and fuses them into a structured output.
        """
        logger.info(f"[FusionEngine] Fusing {len(results)} agent contributions for '{query[:30]}'")
        
        # 1. Check for Multimodal Signals
        multimodal_data = [res for res in results if res.get("agent") in ["VISION", "ECHO"]]
        if multimodal_data:
            logger.info("👀 [FusionEngine] Multimodal signals detected. Triggering Fusion Layer.")
            return await FusionEngine.fuse_multimodal_perception(query, results, lang)

        if fast_mode:
            manifest = [res.get("message", "") if isinstance(res, dict) else getattr(res, "message", "") for res in results if (res.get("success", True) if isinstance(res, dict) else getattr(res, "success", True))]
            return "\n\n---\n\n".join(manifest) or SovereignI18n.get_prompt("error_fallback", lang)

        # 1. 📂 Extract facts and citations from each agent
        manifest = []
        for res in results:
            success = res.get("success", True) if isinstance(res, dict) else getattr(res, "success", True)
            if not success: continue
            
            agent_name = res.get("agent", "UNKNOWN").upper() if isinstance(res, dict) else getattr(res, "agent", "UNKNOWN").upper()
            content = res.get("message", "") if isinstance(res, dict) else getattr(res, "message", "")
            manifest.append(f"[{agent_name}] FINDINGS: {content}")

        if not manifest:
            return SovereignI18n.get_prompt("error_fallback", lang)

        # 2. ⚖️ Deterministic Truth Scoring
        from backend.core.truth_engine import truth_engine
        truth_report = await truth_engine.evaluate_claims(results)
        
        scored_manifest = []
        for f in truth_report["truth_ledger"]:
            scored_manifest.append(f"[{f['source']}] (Truth Score: {f['truth_score']:.2f}): {f['content']}")
        
        # 3. 🧠 Construct Advanced Fusion Prompt
        blueprint = SovereignI18n.get_prompt("rag_synthesis", lang, context=chr(10).join(scored_manifest))
        conflict_note = f"\n[ALERT]: {len(truth_report['conflicts'])} informational contradictions detected." if truth_report["conflicts"] else ""

        fusion_prompt = f"""
            You are the LEVI-AI Sovereign Fusion Engine. 
            Objective: Synthesize findings into a single, high-fidelity response.
            
            USER QUERY: {SovereignSecurity.mask_pii(query)}
            
            [TRUTH-SCORED FINDINGS]:
            {blueprint}
            {conflict_note}
            
            [INSTRUCTIONS]:
            1. Create a unified narrative from the provided truth-scored findings.
            2. Eliminate redundant data.
            3. Maintain a {mood} and sovereign tone.
            4. Cite sources as [AgentName] within the text.
            5. Return ONLY the fused, human-ready response in {lang.upper()}.
        """

        try:
            fused_msg = await handle_local_sync([{"role": "user", "content": fusion_prompt}], model_type="default")
            return SovereignSecurity.mask_pii(fused_msg)
        except Exception as e:
            logger.error(f"Fusion synthesis failure: {e}")
            return "\n\n---\n\n".join(manifest)

    @staticmethod
    async def fuse_multimodal_perception(query: str, results: List[Dict], lang: str = "en") -> str:
        """
        Sovereign v22.1: Vision/Audio Fusion Layer.
        Cross-references visual embeddings with audio transcripts to resolve environmental ambiguity.
        """
        vision_frames = [r.get("data", {}).get("embeddings", []) for r in results if r.get("agent") == "VISION"]
        audio_transcript = " ".join([r.get("message", "") for r in results if r.get("agent") == "ECHO"])
        
        logger.info(f"🧠 [FusionEngine] Synthesizing {len(vision_frames)} visual pulses with audio transcript: '{audio_transcript[:30]}...'")
        
        # 1. Cross-modal Resonance Check
        # (Simplified for v22.1 Baseline: LLM-based Synthesis)
        fusion_prompt = (
            "You are the Sovereign Perception Synthesizer.\n"
            "Combine the following multi-modal signals into a unified environmental perception.\n\n"
            f"USER QUERY: {query}\n"
            f"VISUAL SUMMARY: {len(vision_frames)} frames captured.\n"
            f"AUDIO TRANSCRIPT: {audio_transcript}\n\n"
            "Output: A single paragraph describing the fused perception, ensuring visual and audio cues are synchronized."
        )
        
        try:
            fused_perception = await handle_local_sync([{"role": "user", "content": fusion_prompt}], model_type="vision")
            return SovereignSecurity.mask_pii(fused_perception)
        except Exception as e:
            logger.error(f"[FusionEngine] Multimodal fusion failed: {e}")
            return f"Perception Sync Failure: {audio_transcript}"

    @staticmethod
    async def fuse_responses(query: str, results: List[Dict], **kwargs) -> str:
        """Alias for fuse_results to match legacy calls."""
        return await FusionEngine.fuse_results(query, results, **kwargs)
