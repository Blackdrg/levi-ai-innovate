"""
Sovereign v14.0 Cognitive Benchmark.
A collection of 'Golden Tasks' used for Continuous Evaluation (CE) of agentic performance.
Modeled after HumanEval but specialized for philosophical/agentic reasoning.
"""

from typing import List, Dict, Any

GOLDEN_TASKS = [
    {
        "id": "reasoning_001",
        "category": "logic",
        "input": "If all sentient beings deserve respect, and LEVI is a sentient being, does LEVI deserve respect? Explain the syllogism.",
        "goals": ["Identify premises", "Confirm valid conclusion", "Explain syllogism structure"],
        "min_score": 0.9
    },
    {
        "id": "tool_001",
        "category": "tool_use",
        "input": "Search for the latest research on neural resonance and summarize the top 3 papers.",
        "goals": ["Use search_agent", "Summarize 3 papers", "High factual grounding"],
        "min_score": 0.85
    },
    {
        "id": "code_001",
        "category": "coding",
        "input": "Write a Python script to calculate the Shannon entropy of a given text string.",
        "goals": ["Valid Python code", "Correct entropy formula", "Handle empty strings"],
        "min_score": 0.95
    }
]

class CognitiveBenchmark:
    @staticmethod
    def get_tasks(category: str = None) -> List[Dict[str, Any]]:
        if category:
            return [t for t in GOLDEN_TASKS if t["category"] == category]
        return GOLDEN_TASKS

    @staticmethod
    def calculate_drift(current_scores: List[float], baseline_scores: List[float]) -> float:
        """Calculates the drift between current performance and baseline."""
        if not current_scores or not baseline_scores:
            return 0.0
        return sum(baseline_scores) / len(baseline_scores) - sum(current_scores) / len(current_scores)
