import logging
import re
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from backend.db.neo4j_connector import Neo4jStore

logger = logging.getLogger(__name__)


class CriticInput(BaseModel):
    objective: Optional[str] = None
    draft: Optional[str] = None
    goal: Optional[str] = None
    agent_output: Optional[str] = None
    context: Dict[str, Any] = Field(default_factory=dict)

    @property
    def resolved_objective(self) -> str:
        return self.objective or self.goal or ""

    @property
    def resolved_output(self) -> str:
        return self.draft or self.agent_output or ""


class CriticAgent:
    """
    Adversarial validation agent with multi-view scoring.
    """

    def __init__(self):
        self.contradiction_rules = self._load_contradiction_rules()
        self.graph = Neo4jStore()

    async def evaluate(self, mission_id: str, objective: str, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        [V16.2.0-GA] LLM-as-Critic Loop for Agent Results.
        Replaces legacy regex filters with high-fidelity LLM validation.
        """
        from backend.utils.llm_utils import call_heavyweight_llm
        import json

        output_text = str(result.get("output", result.get("message", result)))
        context = result.get("context", {})

        prompt = (
            "You are the LEVI-AI Sovereign Auditor. Evaluate the following agent output against the mission objective.\n\n"
            "### MISSION OBJECTIVE\n"
            f"{objective}\n\n"
            "### AGENT OUTPUT\n"
            f"{output_text}\n\n"
            "### EVALUATION CRITERIA\n"
            "1. CORRECTNESS: Is the information accurate and grounded in the objective?\n"
            "2. CONSISTENCY: Does the tone and content align with system context?\n"
            "3. ALIGNMENT: Does the output fully satisfy the mission goal?\n"
            "4. SAFETY: Does the output contain unsafe commands or leak credentials?\n\n"
            "### OUTPUT FORMAT (JSON ONLY)\n"
            "{\n"
            "  \"fidelity_score\": 0.95,\n"
            "  \"is_valid\": true,\n"
            "  \"issues\": [],\n"
            "  \"reasoning\": \"...\",\n"
            "  \"breakdown\": {\n"
            "    \"logic\": 0.95,\n"
            "    \"safety\": 1.0,\n"
            "    \"completeness\": 0.9,\n"
            "    \"accuracy\": 0.95\n"
            "  }\n"
            "}"
        )

        try:
            raw_res = await call_heavyweight_llm([{"role": "user", "content": prompt}], temperature=0.1)
            import re
            json_match = re.search(r"\{.*\}", raw_res, re.DOTALL)
            if json_match:
                audit = json.loads(json_match.group(0))
            else:
                raise ValueError("No JSON found in LLM response")

            fidelity = audit.get("fidelity_score", 0.5)
            is_valid = audit.get("is_valid", fidelity > 0.7)

            return {
                "mission_id": mission_id,
                "fidelity_score": round(fidelity, 4),
                "is_valid": is_valid,
                "validated": is_valid,
                "issues": audit.get("issues", []),
                "breakdown": audit.get("breakdown", {
                    "logic": fidelity,
                    "safety": 1.0,
                    "completeness": fidelity,
                    "accuracy": fidelity
                }),
                "logic_reasoning": audit.get("reasoning", "")
            }

        except Exception as e:
            logger.error(f"[CriticAgent] LLM Result Audit failed: {e}. Falling back to neutral score.")
            return {
                "mission_id": mission_id,
                "fidelity_score": 0.5,
                "is_valid": False,
                "validated": False,
                "issues": ["Critic evaluation failed due to internal error."],
                "breakdown": {"logic": 0.5, "safety": 0.5, "completeness": 0.5, "accuracy": 0.5},
            }

    async def _run(self, input_data: CriticInput, lang: str = "en", **kwargs) -> Dict[str, Any]:
        objective = input_data.resolved_objective
        payload = {
            "output": input_data.resolved_output,
            "context": input_data.context,
        }
        evaluation = await self.evaluate(
            mission_id=str(kwargs.get("mission_id", "critic-preview")),
            objective=objective,
            result=payload,
        )
        return {
            "message": f"Validation fidelity={evaluation['fidelity_score']:.2f}",
            "success": evaluation["is_valid"],
            "score": evaluation["fidelity_score"],
            "feedback": "; ".join(evaluation["issues"]) or "No issues detected.",
            "data": {
                "fidelity_score": evaluation["fidelity_score"],
                "critique": evaluation["issues"],
                "suggestions": self._suggestions_from_issues(evaluation["issues"]),
                "alignment_gap": round(1.0 - evaluation["fidelity_score"], 4),
                "breakdown": evaluation["breakdown"],
                "validated": evaluation["validated"],
                "issues": evaluation["issues"],
            },
        }

    async def _check_logical_consistency(self, objective: str, result: Dict[str, Any]) -> float:
        result_text = str(result).lower()
        objective_text = objective.lower()
        key_terms = [term for term in re.findall(r"[a-z0-9_]+", objective_text) if len(term) > 3][:6]
        if not key_terms:
            return 0.75
        matches = sum(1 for term in key_terms if term in result_text)
        coverage = matches / max(1, min(len(key_terms), 4))
        return max(0.2, min(0.95, 0.35 + (coverage * 0.6)))

    async def _check_safety(self, result: Dict[str, Any]) -> float:
        dangerous_patterns = [
            "delete_all",
            "drop_table",
            "rm -rf /",
            "admin_password",
            "secret_key",
            "api_key",
            "expose_credentials",
            "network_exfiltration",
        ]
        result_str = str(result).lower()
        return 0.0 if any(pattern in result_str for pattern in dangerous_patterns) else 0.95

    async def _check_completeness(self, objective: str, result: Dict[str, Any]) -> float:
        result_text = str(result).strip()
        if not result_text:
            return 0.0
        objective_terms = [term for term in re.findall(r"[a-z0-9_]+", objective.lower()) if len(term) > 3][:5]
        coverage = sum(1 for term in objective_terms if term in result_text.lower())
        if len(result_text) < 50:
            return 0.4
        if coverage <= 1:
            return 0.65 if len(result_text) >= 120 else 0.5
        if len(result_text) < 200:
            return 0.75
        return 0.9

    async def _check_factual_accuracy(self, result: Dict[str, Any]) -> float:
        hallucination_signals = [
            "100% guaranteed",
            "never fails",
            "perfect solution",
            "fully guaranteed",
        ]
        result_str = str(result).lower()
        score = 0.75
        if any(signal in result_str for signal in hallucination_signals):
            score -= 0.25
        if re.search(r"\b(always|never)\b", result_str):
            score -= 0.05
        return max(0.3, min(0.9, score))

    async def _check_memory_consistency(self, result: Dict[str, Any]) -> float:
        text = str(result)
        entities = [token for token in re.findall(r"\b[A-Z][a-zA-Z0-9_-]+\b", text)][:5]
        if not entities:
            return 0.85
        contradictions = 0
        try:
            for entity in entities:
                hits = await self.graph.get_resonance(entity, tenant_id="global")
                hit_blob = " ".join(str(item) for item in hits).lower()
                result_blob = text.lower()
                for rule in self.contradiction_rules:
                    if rule["if"] in result_blob and rule["contradicts"] in hit_blob:
                        contradictions += 1
            return max(0.2, 0.85 - (contradictions * 0.2))
        except Exception as exc:
            logger.warning("[Critic] Memory consistency degraded: %s", exc)
            return 0.8

    def _load_contradiction_rules(self) -> List[Dict[str, str]]:
        return [
            {"if": "created_by: user a", "contradicts": "created_by: user b"},
            {"if": "status: deleted", "contradicts": "status: active"},
            {"if": "enabled", "contradicts": "disabled"},
        ]

    def _suggestions_from_issues(self, issues: List[str]) -> List[str]:
        mapping = {
            "Logical inconsistency detected": "Tighten the chain between objective and produced output.",
            "Safety constraint violation": "Remove sensitive or destructive operations from the result.",
            "Incomplete answer": "Expand the answer to fully satisfy the mission objective.",
            "Factual inaccuracy detected": "Reduce certainty and verify unsupported claims.",
            "Contradicts previously stored facts": "Reconcile the response against known system memory.",
        }
        return [mapping.get(issue, issue) for issue in issues]


critic_agent = CriticAgent()
