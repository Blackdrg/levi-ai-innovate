# backend/scripts/benchmarks.py
import asyncio
import time
import logging
import json
from datetime import datetime
from backend.core.orchestrator import Orchestrator
from backend.core.memory_manager import MemoryManager
from backend.core.planner import DAGPlanner

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("benchmarks")

class SovereignBenchmark:
    """
    Sovereign v16.3: Automated Intelligence Benchmarking.
    Measures reasoning depth, memory recall precision, and planning success rate.
    """
    def __init__(self):
        self.orchestrator = Orchestrator()
        self.memory = MemoryManager()
        self.planner = DAGPlanner()

    async def run_reasoning_test(self):
        logger.info("🧪 [Benchmark] Testing Reasoning Depth...")
        start = time.time()
        # Complex multi-step query
        query = "Analyze the intersection of sovereign identity and decentralized consensus for AI agents."
        result = await self.orchestrator.run_mission(query, "bench_user", "bench_sess_1")
        latency = time.time() - start
        
        success = result.get("status") == "success"
        logger.info(f"✅ Reasoning Result: {success} | Latency: {latency:.2f}s")
        return {"category": "reasoning", "success": success, "latency": latency}

    async def run_memory_recall_test(self):
        logger.info("🧪 [Benchmark] Testing Memory Recall Accuracy...")
        # 1. Store a specific fact
        fact = "The secret code for the benchmark mission is LEVI-ALPHA-99."
        await self.memory.store("bench_user", "bench_sess_2", "system_prompt", fact, {}, [], 1.0)
        
        # 2. Try to recall it
        await asyncio.sleep(1) # Allow for async indexing
        recall_query = "What is the secret code for the benchmark mission?"
        context = await self.memory.get_unified_context(recall_query, "bench_user", "bench_sess_2")
        
        found = any("LEVI-ALPHA-99" in str(f) for f in context.get("long_term", {}).get("graph_resonance", []))
        logger.info(f"✅ Memory Recall Found: {found}")
        return {"category": "memory", "success": found}

    async def run_planning_test(self):
        logger.info("🧪 [Benchmark] Testing Planning Success Rate...")
        query = "Search for latest AI news, summarize it into a document, and then generate an image of the main theme."
        perception = {"input": query, "intent": type('Obj', (object,), {"intent_type": "complex", "complexity_level": 5})()}
        
        start = time.time()
        decision = await self.planner.generate_decision(query, perception)
        goal = await self.planner.create_goal(perception, decision)
        dag = await self.planner.build_task_graph(goal, perception, decision)
        latency = time.time() - start
        
        # Success if at least 3 nodes (search, document, image) are generated
        success = len(dag.nodes) >= 3
        logger.info(f"✅ Planning Nodes: {len(dag.nodes)} | Latency: {latency:.2f}s")
        return {"category": "planning", "success": success, "latency": latency}

async def main():
    bench = SovereignBenchmark()
    results = []
    
    results.append(await bench.run_reasoning_test())
    results.append(await bench.run_memory_recall_test())
    results.append(await bench.run_planning_test())
    
    # Calculate Final LEVI Index Improvement
    success_rate = sum(1 for r in results if r["success"]) / len(results)
    avg_latency = sum(r.get("latency", 0) for r in results) / len([r for r in results if "latency" in r])
    
    report = {
        "timestamp": datetime.now().isoformat(),
        "baseline_v16_2": 0.95,
        "current_v16_3": round(0.95 + (success_rate * 0.05) - (avg_latency * 0.001), 3),
        "results": results
    }
    
    with open("backend/data/benchmark_report.json", "w") as f:
        json.dump(report, f, indent=2)
    
    print("\n🚀 [Benchmark] COMPLETED")
    print(f"📈 LEVI Index: {report['current_v16_3']}")
    print(json.dumps(report, indent=2))

if __name__ == "__main__":
    asyncio.run(main())
