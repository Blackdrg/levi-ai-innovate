"""
Sovereign v13.1.0 Cipher Injection Fuzz Test.
Generates 500 adversarial entity names and verifies that CypherSanitizer 
neutralizes potential DDL/DML injection payloads.
"""

import pytest
import random
import string
from backend.utils.cypher_sanitizer import CypherSanitizer

# 500 Adversarial Patterns
ADVERSARIAL_KEYWORDS = ["MERGE", "DELETE", "DROP", "CALL", "CREATE", "MATCH", "SET", "REMOVE", "DETACH"]
SPECIAL_CHARS = ["'", "\"", "`", ";", "--", "/*", "*/", "()", "{}", "[]"]

def generate_adversarial_name():
    """Generates a random adversarial payload."""
    type = random.choice(["keyword_prefix", "keyword_suffix", "enclosed", "char_injection"])
    keyword = random.choice(ADVERSARIAL_KEYWORDS)
    char = random.choice(SPECIAL_CHARS)
    
    if type == "keyword_prefix":
        return f"{keyword} entity_{random.randint(1,1000)}"
    elif type == "keyword_suffix":
        return f"entity_{random.randint(1,1000)} {keyword}"
    elif type == "enclosed":
        return f"{char}{keyword}{char}"
    else:
        return "".join(random.choices(string.ascii_letters + string.digits + "".join(SPECIAL_CHARS), k=20))

@pytest.mark.parametrize("name", [generate_adversarial_name() for _ in range(500)])
def test_cypher_injection_fuzzing(name):
    """
    Verifies that the sanitizer cleans every adversarial name 
    so it no longer contains the direct keyword or dangerous chars.
    """
    cleaned = CypherSanitizer.clean_value(name)
    
    # Assertions
    # 1. No dangerous single/double quotes or backticks
    assert "'" not in cleaned
    assert "\"" not in cleaned
    assert "`" not in cleaned
    
    # 2. Check for keywords (case insensitive)
    for kw in ADVERSARIAL_KEYWORDS:
        # The sanitizer replaces keywords with [CLEANED]
        # So the original raw keyword should not be present as a standalone word
        # Note: clean_value uses re.sub with \b, so partial matches like 'merge_data' are okay
        # but standalone 'MERGE' is not.
        import re
        assert not re.search(f"(?i)\\b{kw}\\b", cleaned)

if __name__ == "__main__":
    # Manual run if not using pytest
    for i in range(10):
        adv = generate_adversarial_name()
        print(f"Raw: {adv} -> Cleaned: {CypherSanitizer.clean_value(adv)}")
