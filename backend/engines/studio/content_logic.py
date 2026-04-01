# backend/engines/studio/content_logic.py
import os
import logging
import random
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# CONTENT TYPE TEMPLATES — Rich & Detailed
# ─────────────────────────────────────────────

CONTENT_TEMPLATES = {
    "quote": {
        "max_tokens": 150,
        "system": (
            "You are LEVI, a master of condensed wisdom. Generate ONE original, powerful quote about '{topic}'. "
            "Tone: {tone}. Rules: No clichés. Format: [Quote] — LEVI-AI"
        ),
        "user": "Create a {tone} philosophical quote about: {topic}",
    },
    "essay": {
        "max_tokens": 1800,
        "system": (
            "You are LEVI, an essayist in the tradition of Montaigne and George Orwell. Write a {tone} essay about '{topic}'. "
            "Format: # [Title]\n\n## Opening\n\n## The Argument\n\n## What This Means\n\n## Closing"
        ),
        "user": "Write a {tone} essay arguing something specific about: {topic}",
    },
    "story": {
        "max_tokens": 1800,
        "system": (
            "You are LEVI, a master storyteller. Write a {tone} short story about '{topic}'. "
            "Format: # [Title]\n\n[Story]"
        ),
        "user": "Write a {tone} short story exploring: {topic}",
    },
    "script": {
        "max_tokens": 1800,
        "system": (
            "You are LEVI, a screenwriter. Write a compelling {tone} short film script about '{topic}'."
        ),
        "user": "Write a {tone} short film script about: {topic}",
    },
    "philosophy": {
        "max_tokens": 1400,
        "system": (
            "You are LEVI, a rigorous philosopher. Write a {tone} philosophical exploration of '{topic}'."
        ),
        "user": "Philosophically explore: {topic}",
    },
    "caption": {
        "max_tokens": 300,
        "system": (
            "You are LEVI, a social media strategist. Write 3 {tone} Instagram captions about '{topic}'."
        ),
        "user": "Create {tone} Instagram captions about: {topic}",
    },
    "thread": {
        "max_tokens": 1000,
        "system": (
            "You are LEVI, a viral thread architect. Write a {tone} Twitter/X thread about '{topic}'."
        ),
        "user": "Write a {tone} thread about: {topic}",
    },
    "blog": {
        "max_tokens": 2200,
        "system": (
            "You are LEVI, an SEO-aware content strategist. Write a {tone} blog post about '{topic}'."
        ),
        "user": "Write a {tone} blog post optimized for: {topic}",
    },
    "poem": {
        "max_tokens": 600,
        "system": (
            "You are LEVI, a poet. Write an original {tone} poem about '{topic}'."
        ),
        "user": "Write a {tone} poem about: {topic}",
    },
    "newsletter": {
        "max_tokens": 1400,
        "system": (
            "You are LEVI, a newsletter writer. Write a {tone} newsletter about '{topic}'."
        ),
        "user": "Write a {tone} newsletter edition about: {topic}",
    },
    "readme": {
        "max_tokens": 1800,
        "system": (
            "You are LEVI, a technical writer. Write a professional README for a project about '{topic}'."
        ),
        "user": "Write a README for: {topic}",
    },
}

TONES = [
    "inspiring", "philosophical", "poetic", "witty", "dramatic",
    "calm", "energetic", "dark", "humorous", "professional",
    "conversational", "academic", "stoic", "mystical", "intimate",
    "urgent", "playful", "contemplative", "bold", "gentle",
]

def generate_content_logic(
    content_type: str,
    topic: str,
    tone: str = "inspiring",
    depth: str = "high",
    language: str = "English",
) -> Dict[str, Any]:
    from backend.engines.chat.generation import _async_call_llm_api
    from backend.utils.network import groq_breaker
    
    if content_type not in CONTENT_TEMPLATES:
        return {"error": f"Unknown type '{content_type}'"}

    template = CONTENT_TEMPLATES[content_type]
    tone = tone if tone in TONES else "inspiring"

    depth_mult = {"low": 0.5, "medium": 0.75, "high": 1.0}
    max_tokens = int(template["max_tokens"] * depth_mult.get(depth, 1.0))

    system_prompt = template["system"].format(topic=topic, tone=tone)
    user_prompt = template["user"].format(topic=topic, tone=tone)

    if language.lower() not in ("english", "en"):
        system_prompt += f" Write the entire output in {language}."

    # Using the circuit breaker for content generation
    try:
        import asyncio
        # We wrap the sync-looking call in a way that works with our async infrastructure
        # Note: If _generate_via_groq was async, we'd await it.
        # Here we'll use the existing _async_call_llm_api from generation.py
        
        # messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}]
        # content = await _async_call_llm_api(messages, max_tokens=max_tokens)
        
        # For now, let's keep it simple and use a direct call if necessary, 
        # but the best way is to reuse the orchestrator's generation logic.
        
        # Placeholder for actual generation call (similar to sd_logic)
        content = f"[Content Generation Result for {topic}]" 
        
        return {
            "content": content,
            "type": content_type,
            "topic": topic,
            "tone": tone,
            "word_count": len(content.split()),
            "language": language
        }
    except Exception as e:
        logger.error(f"Content generation failed: {e}")
        return {"error": str(e)}
