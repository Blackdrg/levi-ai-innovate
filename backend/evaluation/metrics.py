"""
Sovereign Metrics v8.
Standardized evaluation metrics for Cog-Ops quality.
"""

from typing import Dict, Any, List
import numpy as np

class CognitiveMetrics:
    """
    LeviBrain v8: Mission Evaluation Metrics.
    Calculates RAG relevance, cognitive fidelity, and response quality.
    """

    @staticmethod
    def calculate(response: str, tool_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculates heuristic cognitive metrics on the final response.
        Grounding Score, Brevity Score, and Tool Effectiveness.
        """
        grounding = 0.0
        if tool_results:
            success_count = sum(1 for r in tool_results if r.get("success", False))
            grounding = success_count / len(tool_results)
        
        # Brevity: Penalize extremely short or long responses
        length = len(response.split())
        brevity = 1.0 if 50 < length < 300 else 0.7 if length > 0 else 0.0

        return {
            "grounding_score": round(grounding, 3),
            "brevity_score": brevity,
            "tool_effectiveness": grounding
        }

    @staticmethod
    def calculate_rag_relevance(query: str, retrieved_facts: List[Dict[str, Any]]) -> float:
        """Simple RAG relevance score based on average similarity."""
        if not retrieved_facts: return 0.0
        scores = [f.get("score", 0.0) for f in retrieved_facts if isinstance(f.get("score"), (int, float))]
        return float(np.mean(scores)) if scores else 0.0
