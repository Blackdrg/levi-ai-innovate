import asyncio
import os
import sys

# Add current directory to path for imports
sys.path.append(os.getcwd())

from backend.services.orchestrator.agent_registry import AGENTS, call_agent
from backend.services.orchestrator.orchestrator_types import PlanStep, ExecutionPlan
from backend.services.orchestrator.executor import execute_plan

async def test_multi_agent():
    print("--- 🧪 Testing LEVI-AI Multi-Agent System (Phase 1) ---")
    
    # 1. Test Registry
    print("\n[1/4] Checking Agent Registry...")
    expected_agents = ["chat_agent", "search_agent", "image_agent", "code_agent", "document_agent", "memory_agent", "task_agent"]
    for agent in expected_agents:
        if agent in AGENTS:
            print(f"✅ {agent} registered.")
        else:
            print(f"❌ {agent} MISSING in registry.")

    # 2. Test Router (Keyword Path)
    print("\n[2/4] Testing Router (Deterministic Paths)...")
    from backend.agents import RouterAgent
    router = RouterAgent()
    
    latest_query = "What's the latest in quantum computing?"
    res_latest = router.classify_intent(latest_query)
    print(f"Query: '{latest_query}' -> Detected: {res_latest.get('intent')} (Score: {res_latest.get('confidence')})")
    
    doc_query = "According to the PDF, what's my goal?"
    res_doc = router.classify_intent(doc_query)
    print(f"Query: '{doc_query}' -> Detected: {res_doc.get('intent')} (Score: {res_doc.get('confidence')})")

    # 3. Test Parallel Execution (Hybrid)
    print("\n[3/4] Testing Parallel Execution (Hybrid: Chat + Search)...")
    context = {
        "user_id": "test_user_001",
        "input": "Tell me about the latest AI breakthroughs.",
        "user_tier": "pro"
    }
    
    plan = ExecutionPlan(
        intent="hybrid",
        steps=[
            PlanStep(description="Conversational Greeting", agent="chat_agent"),
            PlanStep(description="Web Search Breakthroughs", agent="search_agent")
        ],
        complexity_level=2
    )
    
    print("Executing hybrid plan (Parallel + Fusion)...")
    results = await execute_plan(plan, context)
    
    if results and results[0].agent == "fusion_engine":
        print(f"✅ Hybrid Fusion Successful. Message sample: {results[0].message[:100]}...")
    else:
        print(f"❌ Hybrid Fusion failed or returned wrong agent: {results[0].agent if results else 'None'}")

    # 4. Test New Specialized Agents (Document Agent)
    print("\n[4/4] Testing Specialized Agents (Document Agent)...")
    # This might fail if FAISS isn't initialized, but we can check the error code.
    res_doc_agent = await call_agent("document_agent", {"user_id": "test_user_001", "input": "test query"})
    if res_doc_agent.success:
        print("✅ Document Agent triggered.")
    else:
        print(f"⚠️ Document Agent Error (Expected if no docs): {res_doc_agent.error}")

if __name__ == "__main__":
    asyncio.run(test_multi_agent())
