import logging
from typing import List, Dict
from backend.core.local_engine import handle_local_sync
from backend.engines.utils.security import SovereignSecurity
from backend.engines.utils.i18n import SovereignI18n

logger = logging.getLogger(__name__)

class FusionEngine:
    """
    Sovereign Mind Synthesis Layer.
    Synthesizes multiple agent results (Search, Document, Local, Reasoning) 
    into a single high-fidelity, source-verified response.
    Hardened for Global production.
    """
    
    @staticmethod
    async def fuse_results(query: str, results: List[Dict], lang: str = "en", mood: str = "philosophical", fast_mode: bool = False) -> str:
        """
        Takes multiple agent results and fuses them into a structured output.
        Prioritizes Document Vault > Knowledge Base > Web Pulse.
        Resolves conflicting data using a 'Synthesis Judge' prompt.
        """
        logger.info(f"[FusionEngine] Fusing {len(results)} agent contributions for '{query[:30]}'")
        
        if fast_mode:
            manifest = [res.get("message", "") if isinstance(res, dict) else getattr(res, "message", "") for res in results if (res.get("success", True) if isinstance(res, dict) else getattr(res, "success", True))]
            return "\n\n---\n\n".join(manifest) or SovereignI18n.get_prompt("error_fallback", lang)

        # 1. 📂 Extract facts and citations from each agent
        manifest = []
        for res in results:
            # Handle both AgentResult objects and dictionary results
            success = res.get("success", True) if isinstance(res, dict) else getattr(res, "success", True)
            if not success: continue
            
            agent_name = res.get("agent", "UNKNOWN").upper() if isinstance(res, dict) else getattr(res, "agent", "UNKNOWN").upper()
            content = res.get("message", "") if isinstance(res, dict) else getattr(res, "message", "")
            
            # Formulate a source-aware fact string
            manifest.append(f"[{agent_name}] FINDINGS: {content}")

        if not manifest:
            return SovereignI18n.get_prompt("error_fallback", lang)

        # 2. ⚖️ Deterministic Truth Scoring (Sovereign v16.2 Graduation)
        from backend.core.truth_engine import truth_engine
        truth_report = await truth_engine.evaluate_claims(results)
        
        scored_manifest = []
        for f in truth_report["truth_ledger"]:
            scored_manifest.append(f"[{f['source']}] (Truth Score: {f['truth_score']:.2f}): {f['content']}")
        
        # 3. 🧠 Construct Advanced Fusion Prompt
        # Integrating I18n and Security logic directly into the synthesis
        blueprint = SovereignI18n.get_prompt("rag_synthesis", lang, context=chr(10).join(scored_manifest))
        
        # If conflicts exist, we explicitly inform the synthesizer to handle them based on the ledger resolution
        conflict_note = ""
        if truth_report["conflicts"]:
            conflict_note = f"\n[ALERT]: {len(truth_report['conflicts'])} informational contradictions detected. Prioritize the highest truth-scored finding provided above."

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

        # 3. ⚡ Execute High-Fidelity Synthesis via Council of Models
        messages = [{"role": "system", "content": "You are the Sovereign Synthesizer."}, {"role": "user", "content": fusion_prompt}]
        
        try:
            # Phase 1 Local Shift: Synthesize natively
            fused_msg = await handle_local_sync(messages, model_type="default")
            
            # Final security check on synthesized output
            return SovereignSecurity.mask_pii(fused_msg)
            
        except Exception as e:
            logger.error(f"Fusion synthesis failure: {e}")
            # Fallback: Join them with structured separators
            return "\n\n---\n\n".join(manifest)

    @staticmethod
    async def fuse_responses(query: str, results: List[Dict], **kwargs) -> str:
        """Alias for fuse_results to match legacy calls."""
        return await FusionEngine.fuse_results(query, results, **kwargs)
