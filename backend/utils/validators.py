import re
import json
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

class HardRuleValidator:
    """
    Non-probabilistic validation suite for agentic outputs.
    Provides a "ground truth" score component to break LLM circularity.
    Renamed from 'DeterministicValidator' to reflect its rule-based nature.
    """

    @staticmethod
    def validate(content: str, intent: str = "general") -> Dict[str, float]:
        """
        Calculates an objective score [0.0 - 1.0] based on hard rules.
        """
        scores = {
            "syntax": 1.0,
            "logic": 1.0,
            "grounding": 1.0,
            "resonance": 1.0
        }

        if intent == "code":
            scores["syntax"] = HardRuleValidator._check_code_syntax(content)
        elif intent == "research":
            scores["grounding"] = HardRuleValidator._check_links(content)
        
        # General checks
        scores["logic"] = HardRuleValidator._check_json_integrity(content)
        scores["resonance"] = HardRuleValidator._check_forbidden_patterns(content)

        return scores

    @staticmethod
    def _check_code_syntax(content: str) -> float:
        """AST-based and regex verification of code block completeness."""
        import ast
        
        # Check for open/close triple backticks
        blocks = re.findall(r"```(?:python|py)?\n?([\s\S]*?)```", content)
        if not blocks:
            # If no blocks but intent is code, penalize heavily
            return 0.2 if "def " in content or "class " in content else 0.5
        
        score = 1.0
        for block in blocks:
            # 1. Basic balance check
            if block.count("{") != block.count("}"): score -= 0.1
            if block.count("(") != block.count(")"): score -= 0.1
            
            # 2. Python AST Validation (if applicable)
            try:
                ast.parse(block)
            except SyntaxError:
                # Penalize but don't fail, as it might be a snippet or non-python
                if "def " in block or "import " in block:
                    score -= 0.3
        
        return max(0.0, score)

    @staticmethod
    def _check_links(content: str) -> float:
        """Verifies URL patterns and potential link rot (regex only for now)."""
        urls = re.findall(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', content)
        if not urls:
            return 0.8 # Research without links is less grounded
        
        # Check for suspicious substrings in URLs
        score = 1.0
        for url in urls:
            if "example.com" in url or "yourdomain.com" in url: score -= 0.3 # Placeholders
        
        return max(0.0, score)

    @staticmethod
    def _check_json_integrity(content: str) -> float:
        """Checks if embedded JSON blocks are actually parsable."""
        json_blocks = re.findall(r"```json\n?([\s\S]*?)```", content)
        if not json_blocks:
            return 1.0 # Not required to have JSON
        
        score = 1.0
        for block in json_blocks:
            try:
                json.loads(block)
            except json.JSONDecodeError:
                score -= 0.5
        
        return max(0.0, score)

    @staticmethod
    def _check_forbidden_patterns(content: str) -> float:
        """Enforces 'Resonance' by penalizing forbidden or dangerous strings."""
        # Common local-path or internal-key leak patterns
        forbidden = [
            r"C:\\Users\\[a-zA-Z0-9]+", # Windows paths
            r"/home/[a-zA-Z0-9]+",       # Linux paths
            r"sk-[a-zA-Z0-9]{32,}",      # Potential OpenAI keys
            r"gsk_[a-zA-Z0-9]{32,}"      # Potential Groq keys
        ]
        
        score = 1.0
        for pattern in forbidden:
            if re.search(pattern, content):
                score -= 0.4
        
        return max(0.0, score)
