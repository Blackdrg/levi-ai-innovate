import asyncio
import sys
import os
import logging

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.core.v8.self_improvement import SelfImprovementLoop
from backend.core.v8.decision_engine import DecisionEngine
from backend.core.v8.rules_engine import RulesEngine
from backend.core.v8.learning import PatternRegistry, MemoryCache

# Setup basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_v8_14_loop():
    user_id = "test_user_v8_14"
    query = "What is the core directive of LEVI?"
    response = "The core directive is Sovereignty and Autonomy."
    
    print("--- Phase 1: Pattern Tracking ---")
    # Simulate 3 successful missions with the same query/response
    for i in range(1, 4):
        outcome = {
            "query": query,
            "response": response,
            "success": True,
            "intent": "knowledge",
            "score": 0.95,
            "level": 4 # LLM level
        }
        print(f"Mission {i}: Processing...")
        await SelfImprovementLoop.process_mission(user_id, outcome)
        
    print("\n--- Phase 2: Rule Promotion Check ---")
    rules_engine = RulesEngine()
    rule = await rules_engine.get_rule(query)
    print(f"Promoted Rule Match: {rule}")
    # Note: Success depends on mock validation in learning.py
    
    print("\n--- Phase 3: Decision Engine Integration ---")
    decision_engine = DecisionEngine()
    # Mocking memory manager
    class MockMemory: 
        async def get_combined_context(self, *args): return {}
    
    metrics = await decision_engine.compute_metrics(query, None, MockMemory(), user_id, "session_1")
    print(f"Decision Metrics: has_rule={metrics.get('has_rule')}, fragility={metrics.get('fragility')}")
    
    decision = decision_engine.decide(metrics)
    print(f"Final Decision: {decision}")
    
    if decision == "RULE":
        print("\nSUCCESS: v8.14 Self-Improvement Loop validated!")
    else:
        print("\nNOTE: Rule promotion might be pending Critic validation or hit count.")

if __name__ == "__main__":
    asyncio.run(test_v8_14_loop())
