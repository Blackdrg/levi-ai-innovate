"""
LEVI-AI Truth Engine (v16.2).
Deterministic conflict resolution, truth scoring, and source reliability weighting.
Addresses Gap 5: Memory is Not Truth-Aware.
"""

import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)

@dataclass
class Evidence:
    source: str
    content: str
    reliability: float  # 0.0 to 1.0
    timestamp: datetime
    metadata: Dict[str, Any]

class TruthEngine:
    """
    Sovereign Truth & Consistency Engine.
    Performs programmatic evidence fusion and conflict resolution.
    """

    # Source Reliability Defaults
    SOURCE_WEIGHTS = {
        "DOCUMENT": 0.95,      # User's own local documents
        "REASONING": 0.90,     # Internal cognitive derivation
        "KNOWLEDGE_BASE": 0.85,# Curated sovereign memory
        "SEARCH": 0.70,        # External web pulse
        "GOSSIP": 0.60         # Distributed mesh data
    }

    @classmethod
    async def evaluate_claims(cls, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Takes raw agent results and performs a weighted truth-scoring pass.
        """
        evidences = cls._parse_results_to_evidence(results)
        
        # 1. Group by semantic similarity (Simplified for v16.2 logic)
        # In a full impl, we'd use embeddings to cluster similar 'claims'
        
        # 2. Score each 'claim' based on multi-source support
        scored_findings = cls._compute_truth_scores(evidences)
        
        # 3. Resolve Conflicts
        final_truth, conflicts = cls._resolve_informational_conflicts(scored_findings)
        
        return {
            "truth_ledger": final_truth,
            "conflicts": conflicts,
            "integrity_score": cls._calculate_overall_integrity(final_truth)
        }

    @classmethod
    def _parse_results_to_evidence(cls, results: List[Dict[str, Any]]) -> List[Evidence]:
        evidences = []
        for res in results:
            source = res.get("agent", "UNKNOWN").upper()
            content = res.get("message", "")
            
            # Normalize source name (e.g., SEARCH_AGENT -> SEARCH)
            base_source = "SEARCH" if "SEARCH" in source else source
            base_source = "DOCUMENT" if "DOCUMENT" in source else base_source
            
            reliability = cls.SOURCE_WEIGHTS.get(base_source, 0.5)
            
            evidences.append(Evidence(
                source=base_source,
                content=str(content),
                reliability=reliability,
                timestamp=datetime.now(),
                metadata=res.get("metadata", {})
            ))
        return evidences

    @classmethod
    def _compute_truth_scores(cls, evidences: List[Evidence]) -> List[Dict[str, Any]]:
        """
        Computes a truth score for each evidence based on its source and corroboration.
        """
        findings = []
        for e in evidences:
            # Base score is reliability
            score = e.reliability
            
            # Corroboration pass (Semantic overlap with others)
            corroboration_bonus = 0.0
            for other in evidences:
                if other != e:
                    # Simple token overlap for v16.2 (would be embeddings in v17)
                    overlap = cls._calculate_token_overlap(e.content, other.content)
                    if overlap > 0.6:
                        corroboration_bonus += (other.reliability * 0.2)
            
            findings.append({
                "content": e.content,
                "source": e.source,
                "base_score": score,
                "truth_score": min(1.0, score + corroboration_bonus),
                "timestamp": e.timestamp
            })
        return findings

    @classmethod
    def _resolve_informational_conflicts(cls, findings: List[Dict[str, Any]]) -> (List[Dict[str, Any]], List[Dict[str, Any]]):
        """
        Identifies and resolves contradictions using weighted reliability.
        """
        conflicts = []
        resolved = []
        
        # Heuristic: If two findings have overlap but divergent facts (placeholder logic)
        # Real impl would use an LLM or NLI model to detect contradiction
        
        # For LEVI-AI v16.2, we prioritize the highest scored finding per semantic cluster
        # Sorting by truth score ensures priority
        findings.sort(key=lambda x: x["truth_score"], reverse=True)
        
        for f in findings:
            # Check for conflict with already resolved items
            is_conflicting = False
            for r in resolved:
                if cls._is_contradictory(f["content"], r["content"]):
                    is_conflicting = True
                    conflicts.append({
                        "original": r,
                        "competitor": f,
                        "resolution": "PRIORITIZED_HIGHEST_RELIABILITY"
                    })
                    break
            
            if not is_conflicting:
                resolved.append(f)
                
        return resolved, conflicts

    @staticmethod
    def _calculate_token_overlap(a: str, b: str) -> float:
        words_a = set(a.lower().split())
        words_b = set(b.lower().split())
        if not words_a or not words_b: return 0.0
        intersection = words_a.intersection(words_b)
        return len(intersection) / min(len(words_a), len(words_b))

    @staticmethod
    def _is_contradictory(a: str, b: str) -> bool:
        """
        Hardened Semantic Contradiction Detector (v16.2).
        Identifies informational conflicts by checking for semantic polarities 
        within high-overlap claim clusters.
        """
        a_low = a.lower()
        b_low = b.lower()
        
        # 1. Direct Polar Negations
        # If sentences are nearly identical but one has a negation, it's a conflict
        negations = {"not", "no", "never", "none", "neither", "nor", "fail", "reject", "deny"}
        words_a = set(a_low.split())
        words_b = set(b_low.split())
        
        # Common content words (excluding negations and stop words)
        content_a = words_a - negations
        content_b = words_b - negations
        
        # High overlap check (Jaccard similarity of content)
        if not content_a or not content_b: return False
        overlap = len(content_a & content_b) / len(content_a | content_b)
        
        if overlap > 0.7:
            # Check if one has a negation the other lacks
            has_neg_a = bool(words_a & negations)
            has_neg_b = bool(words_b & negations)
            if has_neg_a != has_neg_b:
                return True
        
        # 2. Antonym/Value Polarities (v16.2 Extension)
        # e.g., 'stock is rising' vs 'stock is falling'
        polarity_pairs = [
            ("rising", "falling"), ("up", "down"), ("increase", "decrease"),
            ("success", "failure"), ("true", "false"), ("valid", "invalid"),
            ("safe", "dangerous"), ("active", "inactive"), ("allowed", "forbidden")
        ]
        
        for p1, p2 in polarity_pairs:
            if (p1 in words_a and p2 in words_b) or (p1 in words_b and p2 in words_a):
                if overlap > 0.5: # If they are talking about the same context
                    return True
        
        return False

    @staticmethod
    def _calculate_overall_integrity(resolved: List[Dict[str, Any]]) -> float:
        if not resolved: return 0.0
        return sum(f["truth_score"] for f in resolved) / len(resolved)

truth_engine = TruthEngine()
