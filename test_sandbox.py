import sys
import unittest
from backend.core.v8.sandbox import SovereignSandbox

class TestSovereignSandbox(unittest.TestCase):
    def test_safe_execution(self):
        code = "result = 1 + 1"
        res = SovereignSandbox.execute(code, context={"result": 0})
        self.assertTrue(res["success"])
        self.assertEqual(res["locals"]["result"], 2)

    def test_restricted_builtins(self):
        # Attempt to use 'eval' which should be restricted
        code = "result = eval('1+1')"
        res = SovereignSandbox.execute(code, context={"result": 0})
        self.assertFalse(res["success"])
        self.assertIn("name 'eval' is not defined", res["stderr"])

    def test_timeout(self):
        # Infinite loop
        code = "while True: pass"
        res = SovereignSandbox.execute(code, timeout=1)
        self.assertFalse(res["success"])
        self.assertIn("timed out", res["stderr"])

if __name__ == "__main__":
    unittest.main()
