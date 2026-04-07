"""
Sovereign Cypher Shield v14.0.0.
Strips DDL/DML keywords from LLM-provided values to prevent Cypher injection.
"""

import re
import logging

logger = logging.getLogger(__name__)

class CypherSanitizer:
    """
    Ensures that strings extracted by LLMs (entities, relations) 
    do not contain Cypher injection payloads.
    """
    
    # Keywords that should never appear in a legitimate entity/relation name
    FORBIDDEN_KEYWORDS = [
        r"(?i)\bMERGE\b",
        r"(?i)\bDELETE\b",
        r"(?i)\bDETACH\b",
        r"(?i)\bDROP\b",
        r"(?i)\bCALL\b",
        r"(?i)\bCREATE\b",
        r"(?i)\bMATCH\b",
        r"(?i)\bSET\b",
        r"(?i)\bREMOVE\b",
        r"(?i)\bFOREACH\b",
    ]

    @classmethod
    def clean_value(cls, value: str) -> str:
        """
        Strips forbidden Cypher keywords and special characters 
        that could be used to break out of parameter scope.
        """
        if not value:
            return ""
            
        cleaned = value
        for pattern in cls.FORBIDDEN_KEYWORDS:
            if re.search(pattern, cleaned):
                logger.warning(f"[CypherShield] Injection attempt neutralized: {pattern}")
                cleaned = re.sub(pattern, "[CLEANED]", cleaned)
        
        # Also strip characters that might be used for manual string escaping 
        # even though we use parameters, extra defense-in-depth.
        cleaned = cleaned.replace("'", "").replace("\"", "").replace("`", "")
        
        return cleaned.strip()

    @classmethod
    def sanitize_triplet(cls, subject: str, relation: str, obj: str) -> tuple[str, str, str]:
        """Convenience wrapper for triplets."""
        return (
            cls.clean_value(subject),
            cls.clean_value(relation),
            cls.clean_value(obj)
        )
