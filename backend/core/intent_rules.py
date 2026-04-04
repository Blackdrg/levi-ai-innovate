"""
Sovereign Intent Rules Registry v1.
Centralized location for high-speed rule-based intent detection patterns.
Decoupled to prevent circular imports between Planner and Classifier.
"""

from typing import List, Dict, Any

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
