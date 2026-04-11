# backend/core/reasoning/confidence.py
import os
import logging
from dataclasses import dataclass
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

@dataclass
class ConfidenceScore:
    base_score: float  # Bayesian combination
    risk_level: str    # low, medium, high, critical
    required_threshold: float
    passes_gate: bool

def calculate_dag_depth(plan: Any) -> int:
    """Calculates the maximum depth of the task graph."""
    if not hasattr(plan, "nodes"): return 0
    # Simple depth heuristic based on sequential dependencies
    return len(plan.nodes) 

def classify_risk(plan: Any) -> str:
    """identify sensitive operations in plan based on keywords."""
    risky_keywords = {
        "critical": ["execute", "delete", "transfer", "modify", "cascade", "destroy"],
        "high": ["analyze", "research", "aggregate", "scrape"],
        "medium": ["search", "fetch", "summarize", "post"],
        "low": ["summarize", "explain", "list", "read"]
    }
    
    # Extract all objectives from nodes
    objectives = []
    if hasattr(plan, "nodes"):
        objectives = [node.objective.lower() for node in plan.nodes]
    
    joined_objectives = " ".join(objectives)
    for level, keywords in risky_keywords.items():
        if any(kw in joined_objectives for kw in keywords):
            return level
    return "low"

async def calculate_confidence(
    plan: Any,
    user_history: Dict[str, Any],
    llm_critique_score: float
) -> ConfidenceScore:
    """
    Sovereign v15.0: Bayesian Confidence Scoring.
    Weights: LLM (0.5), History (0.3), Plan Depth (0.2).
    """
    # 1. Component: LLM Critique (Weight: 0.5)
    score_llm = llm_critique_score
    
    # 2. Component: Historical Success (Weight: 0.3)
    prior_success = user_history.get('success_rate', 0.5)
    
    # 3. Component: Plan Complexity Penalty (Weight: 0.2)
    depth = calculate_dag_depth(plan)
    complexity_penalty = min(depth / 20.0, 1.0) # Max 20 levels before 0 score
    score_depth = (1.0 - complexity_penalty)
    
    # Bayesian Combination
    bayes_confidence = (
        (score_llm * 0.5) +
        (prior_success * 0.3) +
        (score_depth * 0.2)
    )
    
    # Risk-Adaptive Thresholds (ENV-Tunable v15.0)
    risk_level = classify_risk(plan)
    thresholds = {
        "low": float(os.getenv("THRESHOLD_RISK_LOW", "0.55")),
        "medium": float(os.getenv("THRESHOLD_RISK_MEDIUM", "0.75")),
        "high": float(os.getenv("THRESHOLD_RISK_HIGH", "0.90")),
        "critical": float(os.getenv("THRESHOLD_RISK_CRITICAL", "0.95"))
    }
    
    required = thresholds.get(risk_level, 0.75)
    passes = bayes_confidence >= required
    
    logger.info(
        f"[Confidence] Bayesian: {bayes_confidence:.2f} | Risk: {risk_level} "
        f"| Required: {required:.2f} | Result: {'PASS' if passes else 'REJECT'}"
    )
    
    return ConfidenceScore(
        base_score=bayes_confidence,
        risk_level=risk_level,
        required_threshold=required,
        passes_gate=passes
    )
