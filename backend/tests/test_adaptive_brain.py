import sys
import os
import unittest

# Ensure we can import from backend
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from backend.services.orchestrator.brain import LeviBrain
from backend.services.orchestrator.orchestrator_types import EngineRoute

class TestAdaptiveBrain(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.brain = LeviBrain()
        self.user_id = "test_user_adaptive"
        self.session_id = "test_session_adaptive"

    async def test_level_0_greeting(self):
        """Level 0: Should use local_agent and short-circuit."""
        print("\n[Test] Level 0: Greeting")
        result = await self.brain.route(
            user_input="Hello LEVI!",
            user_id=self.user_id,
            session_id=self.session_id
        )
        self.assertEqual(result["decision"]["complexity_level"], 0)
        self.assertEqual(result["route"], EngineRoute.LOCAL.value)
        self.assertIn("response", result)
        print(f"Result: {result['response']}")

    async def test_level_1_simple(self):
        """Level 1: Should use local_agent (single engine)."""
        print("\n[Test] Level 1: Simple Query")
        result = await self.brain.route(
            user_input="What is your purpose?",
            user_id=self.user_id,
            session_id=self.session_id
        )
        self.assertEqual(result["decision"]["complexity_level"], 1)
        self.assertEqual(result["route"], EngineRoute.LOCAL.value)
        print(f"Result: {result['response']}")

    async def test_level_3_complex_code(self):
        """Level 3: Should use multi-engine pipeline (code_agent)."""
        print("\n[Test] Level 3: Complex Code")
        # We mock detect_intent if needed, but let's see if the patterns catch it
        result = await self.brain.route(
            user_input="Write a python script to calculate fibonacci sequence using recursion.",
            user_id=self.user_id,
            session_id=self.session_id,
            user_tier="pro"
        )
        self.assertEqual(result["decision"]["complexity_level"], 3)
        self.assertEqual(result["route"], EngineRoute.API.value)
        self.assertTrue(len(result["plan"]["steps"]) >= 2)
        print(f"Result: {result['response'][:100]}...")

    async def test_exact_match_cache(self):
        """Test that identical queries trigger the cache path."""
        print("\n[Test] Exact Match Cache")
        # First call to populate cache
        await self.brain.route("Unique cache test point.", self.user_id, self.session_id)
        
        # Second call
        result = await self.brain.route("Unique cache test point.", self.user_id, self.session_id)
        self.assertEqual(result["route"], "cache")
        self.assertEqual(result["intent"], "cached")

if __name__ == "__main__":
    unittest.main()
