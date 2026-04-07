"""
Sovereign v13.1.0 Egress Proxy (SSRF) Tests.
Verifies that unauthorized domains and private IP ranges are blocked.
"""

import pytest
from backend.utils.egress import EgressProxy

@pytest.mark.parametrize("url, expected", [
    ("https://api.openai.com/v1/chat", True),
    ("http://localhost:8000/api", True), # Internal allowed
    ("http://postgres:5432", True),      # Docker internal
    ("https://google.com", True),
    ("https://malicious-site.com", False),
    ("http://169.254.169.254/latest/meta-data", False), # AWS Metadata
    ("http://127.0.0.1:22", False),      # Explicit IP loopback block (if not allowlisted)
    ("http://192.168.1.1/admin", False), # Private network
    ("http://10.0.0.1", False),          # Private network
    ("https://example.org", False),      # Not in allowlist
])
def test_egress_validation(url, expected):
    """Verifies that the EgressProxy correctly identifies unauthorized egress."""
    assert EgressProxy.validate_target(url) == expected
