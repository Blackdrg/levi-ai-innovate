import asyncio
import logging
import json
from typing import Dict, Any, List
from datetime import datetime, timezone

from .fidelity import FidelityCritic
from .metrics import CognitiveMetrics
from backend.db.firestore_db import db as firestore_db
from backend.db.postgres import PostgresDB
from sqlalchemy import text


logger = logging.getLogger(__name__)

class AutomatedEvaluator:
    """
    Sovereign Automated Evaluator v8.
    Performs batch evaluation and real-time mission scoring.
    """

    @staticmethod
    async def evaluate_transaction(
        user_id: str,
        session_id: str,
        user_input: str,
        response: str,
        goals: List[str],
        tool_results: List[Dict[str, Any]],
        latency_ms: float
    ) -> Dict[str, Any]:
        """
        Full 360-degree cognitive audit of a LEVI-AI transaction.
        """
        logger.info(f"[Evaluator] Auditing transaction for {user_id}")

        # 1. Fidelity Evaluation (LLM-based Critic)
        critic = FidelityCritic()
        fidelity = await critic.evaluate_mission(user_input, response, goals, tool_results)

        # 2. Heuristic Metrics (Factual grounding, length, etc.)
        metrics = CognitiveMetrics.calculate(response, tool_results)

        # 3. Final Sovereign Score
        # (Fidelity * 0.6) + (Grounding * 0.3) + (Speed * 0.1)
        speed_score = max(0, (10000 - latency_ms) / 10000) # Faster is better
        total_score = (
            fidelity.get("fidelity_score", 0.0) * 0.6 +
            metrics.get("grounding_score", 0.0) * 0.3 +
            speed_score * 0.1
        )

        evaluation_report = {
            "user_id": user_id,
            "session_id": session_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "input": user_input[:500],
            "fidelity": fidelity,
            "metrics": metrics,
            "total_score": round(total_score, 3),
            "latency_ms": latency_ms
        }

        # 4. SELF-EVOLUTION LOOP: Pattern Promotion
        if total_score >= 0.85 and user_id and not str(user_id).startswith("guest:"):
            try:
                from backend.core.v8.evolution_engine import EvolutionEngine
                evo = EvolutionEngine()
                # Promote to deterministic rules if fidelity is high
                evo.learn(user_input, response, quality_score=total_score)
                logger.info(f"[Evaluator] Mission {session_id} fed to Evolution Engine (Score: {total_score:.2f})")
            except Exception as e:
                logger.error(f"[Evaluator] Evolution learning drift: {e}")

        # 5. PERSISTENCE (Audit & Telemetry)
        if user_id and not str(user_id).startswith("guest:"):
            # 4a. Legacy Firestore persistence
            try:
                eval_ref = firestore_db.collection("evaluations").document()
                await asyncio.to_thread(lambda: eval_ref.set(evaluation_report))
            except Exception as e:
                logger.error(f"Firestore evaluation persistence failed: {e}")

            # 4b. v8 Relational Persistence (Postgres)
            try:
                engine = PostgresDB.get_engine()
                if engine:
                    async with PostgresDB._session_factory() as session:
                        # Insert into mission_audits
                        query = text("""
                            INSERT INTO mission_audits 
                            (mission_id, fidelity_score, alignment_score, grounding_score, resonance_score, issues, fix_strategy)
                            VALUES (:m_id, :fid, :aln, :grd, :res, :iss, :fix)
                        """)
                        await session.execute(query, {
                            "m_id": session_id if len(str(session_id)) == 36 else None, # Simplified UUID match
                            "fid": fidelity.get("fidelity_score", 0.0),
                            "aln": fidelity.get("alignment", 0.0),
                            "grd": metrics.get("grounding_score", 0.0),
                            "res": metrics.get("resonance", 0.0),
                            "iss": json.dumps(fidelity.get("issues", [])),
                            "fix": fidelity.get("fix", "")
                        })
                        await session.commit()
                        logger.info(f"[Evaluator] Relational audit saved for mission: {session_id}")
            except Exception as e:
                logger.error(f"Postgres evaluation persistence failed: {e}")


        return evaluation_report

    @staticmethod
    async def run_batch_eval(dataset: List[Dict[str, Any]]):
        """Runs evaluation over a predefined test dataset."""
        logger.info(f"[Evaluator] Starting batch evaluation of {len(dataset)} items.")
        results = []
        for item in dataset:
             res = await AutomatedEvaluator.evaluate_transaction(
                 user_id="system_eval",
                 session_id="batch_001",
                 user_input=item["input"],
                 response=item["output"],
                 goals=item.get("goals", []),
                 tool_results=item.get("tool_results", []),
                 latency_ms=item.get("latency", 1000)
             )
             results.append(res)
        
        avg_score = sum(r["total_score"] for r in results) / len(results) if results else 0
        logger.info(f"[Evaluator] Batch complete. Average Sovereign Score: {avg_score:.3f}")
        return results
