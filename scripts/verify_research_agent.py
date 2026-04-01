import asyncio
import os
import sys

# Add current directory to path for imports
sys.path.append(os.getcwd())

from backend.services.orchestrator.agent_registry import call_agent
from backend.agents import RouterAgent

async def test_deep_research():
    print("--- 🧪 Testing LEVI-AI Deep Research Agent (Phase 3) ---")
    
    # 1. Test Router Detection
    print("\n[1/3] Testing Router (Deep Research Intent)...")
    router = RouterAgent()
    query = "Research the latest advancements in Fusion Energy and provide a detailed analysis."
    res = router.classify_intent(query)
    print(f"Query: '{query}' -> Detected: {res.get('intent')} (Confidence: {res.get('confidence')})")
    
    if res.get('intent') == "research_agent":
        print("✅ Router correctly identified deep research intent.")
    else:
        print(f"❌ Router failed to identify research intent: {res.get('intent')}")

    # 2. Test Agent Execution (Mocked/Static check)
    print("\n[2/3] Checking Research Agent Registry...")
    from backend.services.orchestrator.agent_registry import AGENTS
    if "research_agent" in AGENTS:
        print("✅ research_agent found in registry.")
    else:
        print("❌ research_agent MISSING from registry.")

    # 3. Test multi-step search helper (if possible)
    print("\n[3/3] Checking Research Agent Class (tool_registry)...")
    from backend.services.orchestrator.tool_registry import get_tool
    tool = get_tool("research_agent")
    if tool and tool.name == "research_agent":
        print(f"✅ ResearchAgent class registered as: {tool.description}")
    else:
        print("❌ ResearchAgent NOT found in tool_registry.")

if __name__ == "__main__":
    asyncio.run(test_deep_research())
