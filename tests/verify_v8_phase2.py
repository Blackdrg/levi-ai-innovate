import asyncio
import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), "backend"))

async def test_phase2():
    print("--- Testing LeviBrain v8 Phase 2 (Hardening & Unification) ---")
    
    # 1. Test AgentRegistry Dispatch with v8 Agents
    from backend.core.agent_registry import AgentRegistry
    print("\n1. Testing AgentRegistry Dispatch (v8)...")
    try:
        # Chat mission
        context = {"query": "Hello from Phase 2"}
        result = await AgentRegistry.dispatch("chat", context)
        print(f"Chat Agent Result: {result.success}, Message: {result.message[:50]}...")
        
        # Code mission
        context = {"query": "Write a hello world in Python"}
        result = await AgentRegistry.dispatch("code", context)
        print(f"Code Agent Result: {result.success}, Message: {result.message[:50]}...")
        
        print("✅ AgentRegistry integration successful.")
    except Exception as e:
        print(f"❌ AgentRegistry test failed: {e}")

    # 2. Test Orchestrator v1 Bridge
    from backend.api.orchestrator import handle_chat
    print("\n2. Testing Orchestrator handle_chat...")
    try:
        res = await handle_chat("What is the strategy for Phase 2?", "test_user")
        print(f"Orchestrator Response: {res.get('response')[:50]}...")
        print(f"Intent/Strategy: {res.get('intent')}")
        print("✅ Orchestrator bridge successful.")
    except Exception as e:
        print(f"❌ Orchestrator test failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_phase2())
