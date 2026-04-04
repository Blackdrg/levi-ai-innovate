"""
Sovereign Planning Engine v8.
Generates a task graph (DAG) for cognitive missions.
Contains high-speed rule-based and LLM-based intent detection.
"""

import logging
import json
import re
from typing import List, Dict, Any, Optional
from .orchestrator_types import IntentResult
from .task_graph import TaskGraph, TaskNode
from backend.utils.llm_utils import call_lightweight_llm

logger = logging.getLogger(__name__)

# --- Intent Rules (High Speed) ---
INTENT_RULES: List[Dict[str, Any]] = [
    {
        "intent": "greeting",
        "complexity_level": 0,
        "cost_weight": "low",
        "patterns": [
            r"^\s*(hi|hello|hey|howdy|sup|what'?s up|greetings|good\s+(morning|afternoon|evening|night))\s*[!?.]*\s*$",
            r"^\s*yo\s*$",
            r"^\s*hiya\s*$",
        ],
    },
    {
        "intent": "image",
        "complexity_level": 3,
        "cost_weight": "high",
        "patterns": [
            r"\b(generate|create|draw|make|show|paint)\b.*\b(image|picture|photo|illustration|art|portrait)\b",
            r"\b(visualize|render)\b",
            r"\b(imagine|wallpaper)\b",
        ],
    },
    {
        "intent": "code",
        "complexity_level": 3,
        "cost_weight": "high",
        "patterns": [
            r"\b(write|create|generate|fix|debug|refactor|explain|architect)\b.*\b(code|script|program|function|algorithm|class|logic|snippet)\b",
            r"\b(python|javascript|html|css|cpp|java|rust|golang|sql|typescript|react|nextjs)\b",
            r"```[\s\S]*?```",
        ],
    },
    {
        "intent": "search",
        "complexity_level": 2,
        "cost_weight": "medium",
        "patterns": [
            r"\b(search|find|google|look up|research|who is|what is the latest|where is)\b",
            r"\b(news on|information about|check the status of|real-time data|current events)\b",
        ],
    },
    {
        "intent": "math",
        "complexity_level": 1,
        "cost_weight": "low",
        "patterns": [
            r"^\s*[\d\.\+\-\*\/\(\)\^ \t]+\s*[=|\?]?\s*$",
            r"\b(calculate|solve|what is|compute)\b.*\b([\d\.\+\-\*\/\^]+)\b",
            r"(sin|cos|tan|log|sqrt)\(.*\)"
        ],
    },
    {
        "intent": "document",
        "complexity_level": 2,
        "cost_weight": "medium",
        "patterns": [
            r"\b(summarize|read|analyze|extract)\b.*\b(pdf|document|file|paper|text)\b",
            r"\b(rag|vector|knowledge base)\b",
        ],
    },
    {
        "intent": "knowledge",
        "complexity_level": 2,
        "cost_weight": "medium",
        "patterns": [
            r"\b(relation|graph|neo4j|connection|link)\b",
            r"\b(how is .* related to .*)\b",
        ],
    }
]

def detect_sensitivity(user_input: str) -> bool:
    """Sovereign Shield: Detects PII and sensitive information."""
    text = user_input.lower()
    pii_patterns = [
        r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", # Email
        r"\b(?:\d[ -]*?){13,16}\b", # Credit Card
        r"\b\d{3}-\d{2}-\d{4}\b", # SSN
        r"\b(password|credential|login|secret|private|sensitive|bank|account|api[\s_-]*key)\b"
    ]
    for pattern in pii_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    return False

async def detect_intent(user_input: str) -> IntentResult:
    """Unified intent detection for Perception Layer."""
    text = user_input.lower().strip()
    is_sensitive = detect_sensitivity(user_input)

    # 1. Rules Match
    for rule in INTENT_RULES:
        for pattern in rule["patterns"]:
            if re.search(pattern, text, re.IGNORECASE):
                return IntentResult(
                    intent_type=rule["intent"],
                    complexity_level=rule["complexity_level"],
                    estimated_cost_weight=rule["cost_weight"],
                    confidence_score=0.95,
                    is_sensitive=is_sensitive
                )

    # 2. Default Fallback (Chat)
    return IntentResult(
        intent_type="chat",
        complexity_level=1,
        estimated_cost_weight="low",
        confidence_score=0.7,
        is_sensitive=is_sensitive
    )

class DAGPlanner:
    """
    LeviBrain v8: DAG-Based Planner.
    Decomposes goals into a parallelizable task graph.
    """

    async def build_task_graph(self, goal: Any, perception: Dict[str, Any]) -> TaskGraph:
        intent = perception.get("intent")
        intent_type = intent.intent_type if intent else "chat"
        complexity = intent.complexity_level if intent else 2
        user_input = perception.get("input", "")
        
        graph = TaskGraph()
        
        # 1. Level 0: Fast Path
        if complexity == 0:
            graph.add_node(TaskNode(
                id="t_local", 
                agent="local_agent", 
                description="Fast path synchronous response",
                inputs={"input": user_input}
            ))
            return graph

        # 2. Pipeline Generation
        if intent_type == "search":
             graph.add_node(TaskNode(
                 id="t_search",
                 agent="search_agent",
                 description=f"Retrieve latest data for: {user_input}",
                 inputs={"query": user_input}
             ))
             graph.add_node(TaskNode(
                 id="t_synth",
                 agent="chat_agent",
                 description="Synthesize search results",
                 inputs={"input": user_input, "context": "{{t_search.result}}"},
                 dependencies=["t_search"]
             ))
             
        elif intent_type == "code":
             graph.add_node(TaskNode(
                 id="t_code",
                 agent="code_agent",
                 description="Generate code solution",
                 inputs={"input": user_input}
             ))
             graph.add_node(TaskNode(
                 id="t_verify",
                 agent="python_repl_agent",
                 description="Verify code syntax",
                 inputs={"code": "{{t_code.result}}"},
                 dependencies=["t_code"]
             ))

        else: # Default Chat reasoning
             graph.add_node(TaskNode(
                 id="t_core",
                 agent="chat_agent",
                 description="Primary LLM reasoning pass",
                 inputs={"input": user_input, "mood": perception.get("context", {}).get("mood", "philosophical")}
             ))

        # 3. Reflection Pass (Universal for v8 level 2+)
        if complexity >= 2:
            last_id = graph.nodes[-1].id
            graph.add_node(TaskNode(
                id="t_reflect",
                agent="critic_agent",
                description="Qualitative reflection pass",
                inputs={"draft": f"{{{{{last_id}.result}}}}", "goal": goal.objective},
                dependencies=[last_id],
                critical=False
            ))

        return graph

    async def refine_plan(self, task_graph: TaskGraph, reflection: Dict[str, Any], goal: Any, perception: Dict[str, Any]) -> TaskGraph:
        """
        LeviBrain v8: Plan Refinement.
        Adjusts the DAG based on reflection feedback to address quality issues.
        """
        logger.info("[V8 Planner] Refining plan for goal: %s", goal.goal_id)
        
        # 1. Extract refined instructions from reflection
        issues = reflection.get("issues", [])
        fix_strategy = reflection.get("fix", "Please refine the response based on recent feedback.")
        
        # 2. Add a specialized refinement node (Correction Node)
        # This node will depend on all current leaf nodes
        leaf_ids = [n.id for n in task_graph.nodes if not any(n.id in other.dependencies for other in task_graph.nodes)]
        
        # Add a node for refinement
        from .task_graph import TaskNode
        task_graph.add_node(TaskNode(
            id=f"t_refine_{len(task_graph.nodes)}",
            agent="chat_agent",
            description=f"Cognitive refinement pass: {fix_strategy[:50]}...",
            inputs={
                "input": perception.get("input"),
                "issues": issues,
                "strategy": fix_strategy,
                "previous_context": "{{all_results}}"
            },
            dependencies=leaf_ids,
            critical=True
        ))
        
        return task_graph
