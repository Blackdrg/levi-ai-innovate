import logging
import re
from typing import Dict, Any, List, Optional
from backend.core.orchestrator_types import IntentResult
from backend.memory.manager import MemoryManager

logger = logging.getLogger(__name__)

class DecisionLogic:
    """
    LeviBrain v8.8: Cognitive Decision Engine.
    Computes internal confidence and selects execution level (1-4).
    """

    @staticmethod
    async def compute_metrics(
        user_input: str, 
        intent: IntentResult, 
        memory_manager: MemoryManager,
        user_id: str,
        session_id: str
    ) -> Dict[str, Any]:
        """
        Calculates:
        - internal_confidence (0-1)
        - engine_capability (true/false)
        - memory_match_score (0-1)
        """
        text = user_input.lower().strip()
        
        # 1. Internal Confidence (Rule-based vs LLM-based)
        # Inherit from intent detection, but boost if perfectly matched by a rule
        internal_confidence = intent.confidence_score
        
        # 2. Engine Capability
        engine_capability = False
        capable_engine = None
        
        # Math Detection (Deterministic)
        math_patterns = [
            r"^\s*[\d\.\+\-\*\/\(\)\^ \t]+\s*[=|\?]?\s*$", # Simple expressions
            r"\b(calculate|solve|what is|compute)\b.*\b([\d\.\+\-\*\/\^]+)\b",
            r"(sin|cos|tan|log|sqrt)\(.*\)"
        ]
        if any(re.search(p, text) for p in math_patterns):
            engine_capability = True
            capable_engine = "python_repl_agent"

        # Code Detection
        if intent.intent_type == "code":
            engine_capability = True
            capable_engine = "python_repl_agent"
            
        # Doc/RAG Detection
        if intent.intent_type == "document" or "rag" in text:
            engine_capability = True
            capable_engine = "document_agent"

        # KG / Knowledge Graph Detection (Direct Engine)
        if intent.intent_type == "knowledge" or any(k in text for k in ["relation", "neo4j"]):
            engine_capability = True
            capable_engine = "relation_agent"

        # Search Cache / Research Detection
        if intent.intent_type == "search" or "tavily" in text:
            engine_capability = True
            capable_engine = "research_agent"

        # 3. Memory Match Score (Tiered Scan)
        # Check cache and vector store for existing answers
        memory_match_score = 0.0
        context = await memory_manager.get_combined_context(user_id, session_id, user_input)

        # High-Fidelity Match Detection (Logic-Before-Language)
        # Check Graph Engine resonance for direct triplets
        graph_resonance = context.get("graph_resonance", [])
        if graph_resonance:
            # If we find a direct relation match, boost score
            memory_match_score = 0.95

        # Check Long-Term facts for semantic similarity
        elif context.get("long_term"):
            # Minimal logic for semantic hit
            memory_match_score = 0.75

        elif context.get("short_term"):
            memory_match_score = 0.7
            
        return {
            "internal_confidence": internal_confidence,
            "engine_capability": engine_capability,
            "capable_engine": capable_engine,
            "memory_match_score": memory_match_score
        }

    @staticmethod
    def decide_level(metrics: Dict[str, Any]) -> int:
        """
        Decision Rule:
        IF internal_confidence >= 0.7: -> LEVEL 1 (INTERNAL LOGIC)
        ELSE IF engine_capability == true: -> LEVEL 2 (ENGINE)
        ELSE IF memory_match_score >= 0.6: -> LEVEL 1 (MEMORY SYNTHESIS)
        ELSE: -> LEVEL 4 (LLM FALLBACK)
        """
        if metrics["internal_confidence"] >= 0.7:
            return 1
        if metrics["engine_capability"]:
            return 2
        if metrics["memory_match_score"] >= 0.6:
            return 1
        return 4 # Last resort
