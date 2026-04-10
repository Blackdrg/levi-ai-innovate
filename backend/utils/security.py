import re
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class CypherProtector:
    """
    Sovereign Cypher Protection v14.1.0.
    Hardens the graph engine against injection and unauthorized schema manipulation.
    """
    
    # Keywords that are generally forbidden in user-influenced queries
    FORBIDDEN_KEYWORDS = [
        r"\bCALL\b", # Often used for APOC or Procedures that might be exploitable
        r"\bDETACH\b",
        r"\bDELETE\b", # Allow DELETE if not DETACH? Actually better to restrict user DELETEs
        r"\bDROP\b",
        r"\bCREATE\s+INDEX\b",
        r"\bCREATE\s+CONSTRAINT\b",
        r"\bSET\b", # Restrict setting properties if they can affect internal logic
    ]
    
    # Exceptions that are allowed for system-level logic
    # (These should be used carefully)
    SYSTEM_ALLOWLIST = [
        "apoc.create.uuid()",
        "datetime()"
    ]

    @classmethod
    def validate_query(cls, cypher: str, parameters: Dict[str, Any] = None) -> bool:
        """
        Validates Cypher queries for injection patterns.
        """
        # 1. Detect String Interpolation Attempt
        # Checking for quotes that are directly adjacent to variables (e.g., name: ' + val + ')
        interpolation_pattern = r"['\"][^'\"]*['\"]\s*[\+\|]"
        if re.search(interpolation_pattern, cypher):
            logger.error(f"[CypherShield] Possible string interpolation detected: {cypher}")
            return False

        # 2. Check for Forbidden Keywords
        for pattern in cls.FORBIDDEN_KEYWORDS:
            if re.search(pattern, cypher, re.IGNORECASE):
                # Check if it's in the allowlist exceptions
                is_exception = False
                for exception in cls.SYSTEM_ALLOWLIST:
                    if exception in cypher:
                        is_exception = True
                        break
                
                if not is_exception:
                    logger.error(f"[CypherShield] Forbidden keyword '{pattern}' detected in query: {cypher}")
                    return False

        # 3. Parameterization Check
        # User input should ONLY be passed via $parameters.
        # Detecting raw concatenation of likely user variables.
        if parameters:
            for key in parameters.keys():
                # If the key is found in the query without a '$' prefix, it might be an injection attempt
                # (Simple heuristic)
                if re.search(rf"\b{re.escape(key)}\b", cypher) and not re.search(rf"\${re.escape(key)}", cypher):
                     logger.warning(rf"[CypherShield] Potential raw variable exposure: {key}")
        
        return True

    @classmethod
    def sanitize_label(cls, label: str) -> str:
        """Sanitizes dynamic labels to prevent label injection."""
        return re.sub(r"[^a-zA-Z0-0_]", "", label)

    @classmethod
    def sanitize_property_name(cls, name: str) -> str:
        """Sanitizes property names to prevent property injection."""
        return re.sub(r"[^a-zA-Z0-0_]", "", name)
