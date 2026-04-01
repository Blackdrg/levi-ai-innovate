import asyncio
import os
import sys

# Add current directory to path for imports
sys.path.append(os.getcwd())

from backend.services.orchestrator.planner import DynamicBrainScorer, detect_orchestration_route
from backend.learning import AdaptivePromptManager, collect_interaction_log

async def verify_learning_system():
    print("--- 🧪 Testing LEVI-AI Self-Learning Brain (Phase 2) ---")

    # 1. Test Dynamic Routing Config
    print("\n[1/3] Testing Dynamic Routing Config...")
    try:
        config = await DynamicBrainScorer.get_routing_config()
        if "keywords" in config:
            print("✅ Routing config loaded (or defaults used).")
        else:
            print("❌ Routing config structure invalid.")
    except Exception as e:
        print(f"❌ Routing config error: {e}")

    # 2. Test Interaction Logging
    print("\n[2/3] Testing Interaction Logging...")
    try:
        await collect_interaction_log(
            query="Test query for learning",
            route="chat",
            latency_ms=500,
            success=True,
            user_id="test_user_002"
        )
        print("✅ Interaction log collected (check Firestore interaction_logs).")
    except Exception as e:
        print(f"❌ Interaction logging error: {e}")

    # 3. Test Adaptive Prompt Manager (Tuned Values)
    print("\n[3/3] Testing Adaptive Prompt Manager...")
    try:
        pm = AdaptivePromptManager()
        prompt, idx, temp = await pm.get_best_variant("philosophical")
        print(f"✅ Best variant selected: Index {idx}, Temp {temp:.2f}")
        
        # Test trigger auto evolution
        # This will only evolve if scores are poor, but we check if it runs without error
        await pm.trigger_auto_evolution()
        print("✅ Auto-evolution trigger executed.")
    except Exception as e:
        print(f"❌ Prompt manager error: {e}")

if __name__ == "__main__":
    asyncio.run(verify_learning_system())
