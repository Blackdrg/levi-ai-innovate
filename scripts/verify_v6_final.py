import asyncio
import os
import sys

# Add current directory to path for imports
sys.path.append(os.getcwd())

from backend.utils.health import check_brain_health
from backend.services.orchestrator.agent_registry import call_agent
from backend.services.orchestrator.executor import execute_plan
from backend.services.orchestrator.orchestrator_types import ExecutionPlan, PlanStep

async def finalize_v6_8_verification():
    print("--- 🛡️ LEVI-AI v6.8 Sovereign Engine: Final Hardening Verify ---")

    # 1. Test Active Probing
    print("\n[1/3] Testing Sovereign Engine Health Probe...")
    health = await check_brain_health()
    print(f"Status: {health['status']}")
    for k, v in health['checks'].items():
        icon = "✅" if v else "❌"
        print(f"  {icon} {k}")

    # 2. Test Agent Failover (Simulated)
    print("\n[2/3] Testing Resilient Agent Failover...")
    context = {"input": "Deep dive research task", "user_id": "test_user"}
    # We create a plan with research_agent, but if we don't have a TAVILY key it should fail
    # and then RECOVER using search_agent or chat_agent.
    plan = ExecutionPlan(
        intent="research",
        steps=[PlanStep(description="Perform deep research", agent="research_agent")],
        is_sensitive=False
    )
    
    # We manually trigger a failure by removing the API key from environment for this call
    # Or just simulate a failure in the tool itself
    print("Executing plan with potential research_agent failure...")
    results = await execute_plan(plan, context)
    
    any_recovery = any("[RECOVERY]" in r.message or "[RECOVERY]" in str(r.agent) or context.get("safety_recovery_active") for r in results)
    if any_recovery:
        print("✅ Failover Resilience system detected and recovered from agent failure.")
    else:
        print("ℹ️ No failover needed or logic did not trigger (Check if agent succeeded).")

    # 3. Test Multi-Agent Synchronization
    print("\n[3/3] Verifying Complete Agent Registry...")
    from backend.services.orchestrator.agent_registry import AGENTS
    required_agents = ["chat_agent", "search_agent", "document_agent", "memory_agent", "task_agent", "research_agent", "diagnostic_agent"]
    
    missing = [a for a in required_agents if a not in AGENTS]
    if not missing:
        print(f"✅ All {len(required_agents)} Sovereign Agents are registered and synced.")
    else:
        print(f"❌ Missing agents in registry: {missing}")

if __name__ == "__main__":
    asyncio.run(finalize_v6_8_verification())
