import asyncio
import os
import sys

# Add current directory to path for imports
sys.path.append(os.getcwd())

from backend.services.orchestrator.planner import detect_sensitivity, detect_intent
from backend.utils.encryption import SovereignVault
from backend.services.orchestrator.executor import execute_plan
from backend.services.orchestrator.orchestrator_types import ExecutionPlan, PlanStep

async def verify_sovereign_shield():
    print("--- 🧪 Testing LEVI-AI Sovereign Shield (Phase 4) ---")

    # 1. Test Sensitivity Detection
    print("\n[1/3] Testing Sensitivity Detection...")
    queries = [
        ("What is the meaning of life?", False),
        ("My email is test@example.com", True),
        ("Remind me of my bank password", True),
        ("How is the weather in London?", False)
    ]
    
    for q, expected in queries:
        detected = detect_sensitivity(q)
        status = "✅" if detected == expected else "❌"
        print(f"{status} Query: '{q}' -> Sensitive: {detected}")

    # 2. Test Encryption Vault
    print("\n[2/3] Testing Encryption Vault...")
    secret = "This is a profound truth."
    encrypted = SovereignVault.encrypt(secret)
    decrypted = SovereignVault.decrypt(encrypted)
    
    if encrypted != secret and decrypted == secret:
        print(f"✅ Vault working correctly. Plain: '{secret}' -> Cipher: {encrypted[:20]}...")
    else:
        print(f"❌ Vault failed. Decrypted: '{decrypted}'")

    # 3. Test Shield Enforcement (Executor)
    print("\n[3/3] Testing Shield Enforcement in Executor...")
    context = {"input": "My bank password is hidden", "user_id": "test_user"}
    plan = ExecutionPlan(
        intent="sensitive_local",
        steps=[PlanStep(description="Handle sensitivity", agent="chat_agent")],
        is_sensitive=True
    )
    
    print("Executing sensitive plan (Enforcing Shield)...")
    # We check if step description was overridden
    results = await execute_plan(plan, context)
    
    if plan.steps[0].agent == "local_agent" and "[SHIELDED]" in plan.steps[0].description:
        print("✅ Executor forced local_agent and shielded description.")
    else:
        print(f"❌ Shield enforcement failed. Agent: {plan.steps[0].agent}")

if __name__ == "__main__":
    asyncio.run(verify_sovereign_shield())
