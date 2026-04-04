import unittest
import json
import asyncio
from backend.utils.usage import count_tokens, estimate_cost
from backend.services.compliance import generate_audit_signature
from backend.core.orchestrator_types import ToolResult

class TestCompetitiveFeatures(unittest.TestCase):

    def test_token_counting(self):
        """ Verify tiktoken integration and local estimation. """
        text = "Sovereign intelligence requires architectural isolation."
        tokens = count_tokens(text, "gpt-4")
        self.assertGreater(tokens, 0)
        self.assertEqual(tokens, 6) # "Sovereign intelligence requires architectural isolation." is 6 tokens in cl100k
        
        cost = estimate_cost(1000, "gpt-4")
        self.assertEqual(cost, 0.03)

    def test_compliance_signature(self):
        """ Verify HMAC-SHA256 audit pulse integrity. """
        sig1 = generate_audit_signature("user1", "login", "success")
        sig2 = generate_audit_signature("user1", "login", "success")
        self.assertEqual(sig1, sig2)
        
        sig3 = generate_audit_signature("user2", "login", "success")
        self.assertNotEqual(sig1, sig3)

    def test_hitl_tool_result(self):
        """ Verify ToolResult schema compliance. """
        res = ToolResult(success=True, message="Approved", agent="human_approval")
        self.assertTrue(res.success)
        self.assertEqual(res.agent, "human_approval")

if __name__ == "__main__":
    unittest.main()
