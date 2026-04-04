import sys
import unittest
import asyncio
from datetime import datetime, timezone
import os

# Mocking necessary parts for standalone test
class MockMemory:
    pass

class TestUpgrades(unittest.TestCase):
    def test_resonance_formula(self):
        from backend.memory.resonance import MemoryResonance
        # R = (I * 0.4) + (R * 0.2) + (U * 0.2) + (S * 0.2)
        # importance=1.0, recency=1.0 (age=0), usage=1.0 (access=20), success=1.0
        # R = (1.0*0.4) + (1.0*0.2) + (1.0*0.2) + (1.0*0.2) = 1.0
        res = MemoryResonance.calculate_resonance(1.0, datetime.now(timezone.utc), access_count=20, success_impact=1.0)
        self.assertEqual(res, 1.0)
        
        # Test decay
        # importance=0.5, recency=0.66 (age=10), usage=0.0 (access=0), success=0.5
        # recency = 1 / (1 + 10*0.05) = 1 / 1.5 = 0.666
        # usage = 0 / 20 = 0
        # R = (0.5*0.4) + (0.666*0.2) + (0*0.2) + (0.5*0.2) 
        # R = 0.2 + 0.1332 + 0 + 0.1 = 0.4332
        import datetime as dt
        ten_days_ago = datetime.now(timezone.utc) - dt.timedelta(days=10)
        res_decay = MemoryResonance.calculate_resonance(0.5, ten_days_ago, access_count=0, success_impact=0.5)
        self.assertAlmostEqual(res_decay, 0.4333, places=3)

    def test_reinforcement_reward(self):
        from backend.core.v8.learning import ReinforcementLearner
        # reward = success - (token_cost + latency_penalty + tool_cost)
        # success=1.0, latency=1000ms, tools=2, tokens=100
        # token_cost = 100 * 0.0001 = 0.01
        # latency_penalty = 1.0 * 0.1 = 0.1
        # tool_cost = 2 * 0.05 = 0.1
        # cost = 0.21
        # reward = 1.0 - 0.21 = 0.79
        reward = ReinforcementLearner.calculate_reward(1.0, 1000, 2, 100)
        self.assertAlmostEqual(reward, 0.79, places=2)

if __name__ == "__main__":
    unittest.main()
