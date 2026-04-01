"""
backend/services/orchestrator/meta_planner.py

LEVI v6: Meta-Brain reasoning engine.
Handles goal decomposition and adaptive strategy selection.
"""

import logging
import json
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from .orchestrator_types import IntentResult, ExecutionPlan, PlanStep
from backend.generation import _async_call_llm_api
from .local_engine import handle_local_sync, is_locally_handleable

logger = logging.getLogger(__name__)

class SubGoal(BaseModel):
    description: str
    target_agent: str
    dependencies: List[str] = Field(default_factory=list, description="IDs of subgoals that must complete first")
    goal_id: str = Field(default_factory=lambda: f"goal_{__import__('uuid').uuid4().hex[:6]}")

class GoalStrategy(BaseModel):
    overall_strategy: str
    subgoals: List[SubGoal]
    recommended_model: str = "llama-3.1-8b-instant"

async def decompose_goal(user_input: str, intent: IntentResult, context: Dict[str, Any]) -> GoalStrategy:
    """
    LEVI v6: Goal Decomposition & Optimization.
    Incorporates real-time Tool Ledger feedback to adapt strategies.
    """
    from backend.db.redis_client import HAS_REDIS, r as redis_client
    import hashlib
    import json

    # ── 🟢 1. Deterministic Fast-Path (v6 Optimization) ─────────────────────
    if intent.intent in ("greeting", "simple_query"):
        if HAS_REDIS: redis_client.hincrby("benchmarks:meta_brain", "fast_path_hits", 1)
        logger.info(f"[MetaBrain] Fast-path triggered for: {intent.intent}")
        return GoalStrategy(
            overall_strategy="Direct contextual response (Zero-LLM Fast Path)",
            subgoals=[SubGoal(description="Execute immediate response", target_agent="local_agent")],
            recommended_model="none"
        )

    # ── 🔍 2. Strategy Caching ──────────────────────────────────────────────
    cache_key = f"meta_strategy:{hashlib.md5((user_input + intent.intent).encode()).hexdigest()}"
    if HAS_REDIS:
        cached = redis_client.get(cache_key)
        if cached:
            redis_client.hincrby("benchmarks:meta_brain", "cache_hits", 1)
            logger.info("[MetaBrain] Strategy Cache Hit.")
            return GoalStrategy(**json.loads(cached))

    # ── 🧠 3. Adaptive Performance Context (v6 Phase 2) ─────────────────────
    performance_context = ""
    if HAS_REDIS:
        agents = ['chat_agent', 'image_agent', 'code_agent', 'search_agent', 'python_repl_agent', 'video_agent']
        ledger_info = []
        for agent in agents:
            try:
                stats = redis_client.hgetall(f"ledger:agent:{agent}")
                if stats:
                    total = int(stats.get(b"total_calls", 0))
                    failures = int(stats.get(b"failure_calls", 0))
                    if total > 0 and (failures / total) > 0.2: # 20% failure threshold
                        ledger_info.append(f"{agent} is unstable (failure rate: {failures/total:.1%})")
            except Exception:
                continue # Redis might be unstable, don't crash the planner
        
        if ledger_info:
            performance_context = "\n[SYSTEM ADVISORY]: " + " | ".join(ledger_info) + ". Prefer fallbacks if possible."

    system_prompt = (
        "You are the LEVI Meta-Brain. Your goal is to break a high-level human problem into a logical execution strategy.\n"
        "Sovereign Team Agents:\n"
        "- 'chat_agent': General conversational reasoning and persona maintenance.\n"
        "- 'search_agent': Real-time information, news, and surface-level web lookups.\n"
        "- 'research_agent': Deep recursive research (Phase-based discovery, analysis, and global citations).\n"
        "- 'document_agent': Private RAG (Uses uploaded PDFs, TXT, and workspace files).\n"
        "- 'memory_agent': User trait retrieval (Recalls preferences, personality, and history from long-term memory).\n"
        "- 'task_agent': Step-by-step logic, plans, and technical workflows.\n"
        "- 'diagnostic_agent': Internal system health, self-healing, and reasoning RCA.\n\n"
        f"{performance_context}\n\n"
        "Strategy Optimization Guidelines:\n"
        "1. For complex, multi-source, or academic queries, ALWAYS lead with 'research_agent'.\n"
        "2. If a query references 'my files', 'the document', or 'this pdf', use 'document_agent'.\n"
        "3. Incorporate 'memory_agent' for any request requiring personal personalization.\n"
        "4. Parallel Performance: Cluster subgoals to minimize dependency on previous steps. Independent subgoals enable 'Parallel Pulse' execution.\n"
        "5. Output ONLY JSON:\n"
        "{\n"
        "  'overall_strategy': 'Explanation',\n"
        "  'recommended_model': 'llama-3.1-70b-versatile' or 'llama-3.1-8b-instant',\n"
        "  'subgoals': [{ 'description': '...', 'target_agent': '...', 'dependencies': [] }]\n"
        "}"
    )
    
    # Model Router Logic
    model_choice = "llama-3.1-70b-versatile" if intent.complexity >= 6 else "llama-3.1-8b-instant"

    try:
        # ── 🟢 4. Sovereign Local Decomposition (v6 Hardened) ────────────────
        # Use local LLM for managing its own agent flows if complexity is low.
        if intent.complexity < 3 and is_locally_handleable("planner", intent.complexity):
            logger.info("[MetaBrain] Local Decomposition triggered for Complexity L%d", intent.complexity)
            raw_json = await handle_local_sync(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Decompose this task: {user_input} (Intent: {intent.intent})"}
                ],
                temperature=0.1
            )
        else:
            # High-complexity fallback to robust external APIs
            raw_json = await _async_call_llm_api(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Decompose this task: {user_input} (Intent: {intent.intent})"}
                ],
                model=model_choice,
                temperature=0.2,
                max_tokens=600
            )
        
        # Parse result
        content = raw_json.strip()
        if "```json" in content: content = content.split("```json")[1].split("```")[0]
        elif "```" in content: content = content.split("```")[1].split("```")[0]

        data = json.loads(content.strip())
        strategy = GoalStrategy(**data)
        
        if HAS_REDIS:
            redis_client.setex(cache_key, 600, strategy.json()) # Cache for 10 mins
            
        return strategy

    except Exception as e:
        logger.error(f"[MetaBrain] Decomposition failed: {e}")
        return GoalStrategy(
            overall_strategy="Fallback to direct reasoning",
            subgoals=[SubGoal(description="Execute direct response", target_agent="chat_agent")],
            recommended_model="llama-3.1-8b-instant"
        )
