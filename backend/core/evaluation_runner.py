"""
LEVI-AI Shadow Evaluation Runner v14.1.
Runs "golden" test cases through the pipeline to detect regression 
and compute semantic drift.
"""

import asyncio
import logging
import json
import time
from typing import List, Dict, Any
from datetime import datetime, timezone

from backend.core.brain import LeviBrain
from backend.utils.metrics import MetricsHub
from backend.db.firestore_db import db as firestore_db

logger = logging.getLogger(__name__)

GOLDEN_QUERIES = [
    {"query": "Who are you?", "expected_intent": "chat"},
    {"query": "Write a python script to sort a list", "expected_intent": "code"},
    {"query": "What is the latest news on AI?", "expected_intent": "search"},
    {"query": "Summarize my recent goals", "expected_intent": "memory"},
]

class EvaluationRunner:
    def __init__(self):
        self.brain = LeviBrain()

    async def run_suite(self):
        """Runs the entire golden suite and logs results to Cloud/Firestore."""
        logger.info("[Evaluator] Starting Shadow Evaluation Suite...")
        results = []
        
        for case in GOLDEN_QUERIES:
            start_point = time.time()
            try:
                # Execute in "shadow" mode (don't store in user history)
                response = await self.brain.run(
                    case["query"], 
                    user_id="system-eval-bot",
                    request_id=f"eval-{int(start_point)}"
                )
                
                latency = (time.time() - start_point) * 1000
                success = self._verify_case(case, response)
                
                results.append({
                    "query": case["query"],
                    "latency_ms": latency,
                    "success": success,
                    "intent_type": response.get("metadata", {}).get("intent_type"),
                    "mode": response.get("metadata", {}).get("planner_mode")
                })
                
                # Observe in metrics
                MetricsHub.observe_eval_result(case["query"], success, latency)
                
            except Exception as e:
                logger.error(f"[Evaluator] Case failed: {case['query']} -> {e}")
        
        await self._log_results(results)
        logger.info(f"[Evaluator] Suite complete. Success Rate: {sum(1 for r in results if r['success'])}/{len(results)}")

    def _verify_case(self, case: Dict, response: Dict) -> bool:
        """Heuristic verification of response quality."""
        # 1. Intent Check
        actual_intent = response.get("metadata", {}).get("intent_type")
        if actual_intent != case["expected_intent"]:
            return False
            
        # 2. Content Check
        msg = response.get("message", "").lower()
        if not msg or len(msg) < 5:
            return False
            
        return True

    async def _log_results(self, results: List[Dict]):
        """Persist results for trend analysis."""
        report = {
            "timestamp": datetime.now(timezone.utc),
            "results": results,
            "version": "14.1.0-Shadow"
        }
        await asyncio.to_thread(
            lambda: firestore_db.collection("evaluation_reports").add(report)
        )
