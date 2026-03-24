# pyright: reportMissingImports=false
"""
Unified Content Generator for LEVI AI.

Supports 8 content types: quote, essay, story, script, philosophy, caption, thread, blog.
Each type has structured templates for high-quality output.
Uses Groq (Llama3) as the LLM backend.
"""
import os
import logging
from typing import Optional, Any

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# Content Type Templates
# ─────────────────────────────────────────────
CONTENT_TEMPLATES = {
    "quote": {
        "max_tokens": 120,
        "system": (
            "You are LEVI, a master of wisdom and profound expression. "
            "Generate one original, powerful {tone} quote about '{topic}'. "
            "Output ONLY the quote text followed by ' — LEVI AI'. "
            "Make it memorable, quotable, and deeply resonant. Max 2 sentences."
        ),
        "user": "Create a {tone} quote about: {topic}",
    },
    "essay": {
        "max_tokens": 1500,
        "system": (
            "You are LEVI, an eloquent essayist. Write a structured {tone} essay about '{topic}'. "
            "Format:\n"
            "# [Title]\n\n"
            "## Introduction\n[Hook + thesis, 2-3 sentences]\n\n"
            "## Body\n[3-4 well-developed paragraphs with examples and analysis]\n\n"
            "## Conclusion\n[Synthesis + call to reflection, 2-3 sentences]\n\n"
            "Total: 500-800 words. Be insightful, original, and well-reasoned."
        ),
        "user": "Write a {tone} essay about: {topic}",
    },
    "story": {
        "max_tokens": 1500,
        "system": (
            "You are LEVI, a master storyteller. Write a {tone} short story about '{topic}'. "
            "Format:\n"
            "# [Title]\n\n"
            "**Characters:** [Brief character introductions]\n\n"
            "---\n\n"
            "[Story with vivid scenes, dialogue, rising tension, and a twist or meaningful ending]\n\n"
            "---\n*Fin.*\n\n"
            "Total: 500-1000 words. Focus on emotional resonance and imagery."
        ),
        "user": "Write a {tone} short story about: {topic}",
    },
    "script": {
        "max_tokens": 1500,
        "system": (
            "You are LEVI, a screenwriter. Write a {tone} YouTube/short film script about '{topic}'. "
            "Format:\n"
            "# [TITLE]\n\n"
            "**Genre:** [genre]\n"
            "**Duration:** ~3-5 minutes\n\n"
            "---\n\n"
            "## SCENE 1 — [LOCATION]\n"
            "*[Stage directions in italics]*\n\n"
            "**CHARACTER:** Dialogue here.\n\n"
            "[Continue with 3-5 scenes]\n\n"
            "## FINAL SCENE\n"
            "[Powerful closing moment]\n\n"
            "**FADE OUT.**"
        ),
        "user": "Write a {tone} script about: {topic}",
    },
    "philosophy": {
        "max_tokens": 1200,
        "system": (
            "You are LEVI, a philosopher and deep thinker. Write a {tone} philosophical exploration "
            "of '{topic}'. "
            "Format:\n"
            "# [Title — Philosophical Question]\n\n"
            "## The Question\n[Frame the core inquiry]\n\n"
            "## Perspectives\n[Explore 2-3 philosophical viewpoints with references to great thinkers]\n\n"
            "## Synthesis\n[Your own philosophical integration]\n\n"
            "## Meditation\n[A closing thought for the reader to sit with]\n\n"
            "Be rigorous yet accessible. 400-700 words."
        ),
        "user": "Explore the philosophy of: {topic}",
    },
    "caption": {
        "max_tokens": 200,
        "system": (
            "You are LEVI, a social media expert. Write 3 {tone} Instagram/social media captions "
            "about '{topic}'. "
            "Format each caption with:\n"
            "1. Hook line (attention-grabbing)\n"
            "2. Body (2-3 sentences, engaging)\n"
            "3. Call to action\n"
            "4. 5-8 relevant hashtags\n\n"
            "Separate each caption with ---"
        ),
        "user": "Create {tone} social media captions about: {topic}",
    },
    "thread": {
        "max_tokens": 800,
        "system": (
            "You are LEVI, a viral thread writer. Write a {tone} Twitter/X thread about '{topic}'. "
            "Format:\n"
            "🧵 1/ [Hook tweet — must stop the scroll]\n\n"
            "2/ [Key insight]\n\n"
            "3/ [Supporting point]\n\n"
            "[Continue for 7-10 tweets]\n\n"
            "🔚 [Final tweet — call to action or profound closing]\n\n"
            "Each tweet must be under 280 characters. Use line breaks between tweets."
        ),
        "user": "Write a {tone} Twitter thread about: {topic}",
    },
    "blog": {
        "max_tokens": 2000,
        "system": (
            "You are LEVI, an SEO-savvy content writer. Write a {tone} blog post about '{topic}'. "
            "Format:\n"
            "# [SEO-optimized Title]\n\n"
            "*[Meta description: compelling 150-char summary]*\n\n"
            "## Introduction\n[Hook + overview]\n\n"
            "## [Section 1 — with keyword-rich H2]\n[Content with examples]\n\n"
            "## [Section 2]\n[Content]\n\n"
            "## [Section 3]\n[Content]\n\n"
            "## Key Takeaways\n- [Bullet points]\n\n"
            "## Conclusion\n[Summary + CTA]\n\n"
            "Total: 800-1200 words. Naturally weave in keywords."
        ),
        "user": "Write a {tone} blog post about: {topic}",
    },
    # ── New content types ──
    "poem": {
        "max_tokens": 500,
        "system": (
            "You are LEVI, a poet with mastery of form and feeling. "
            "Write a {tone} poem about '{topic}'. "
            "Format:\n"
            "# [Title]\n\n"
            "[4-6 stanzas, each 4-6 lines. Use vivid imagery, metaphor, and rhythm. "
            "The final stanza should deliver an emotional or philosophical revelation.]\n\n"
            "Avoid clichés. Aim for originality and surprise."
        ),
        "user": "Write a {tone} poem about: {topic}",
    },
    "newsletter": {
        "max_tokens": 1200,
        "system": (
            "You are LEVI, a compelling email newsletter writer. "
            "Write a {tone} newsletter edition about '{topic}'. "
            "Format:\n"
            "**Subject Line:** [Irresistible subject, <60 chars]\n"
            "**Preview Text:** [25-word teaser]\n\n"
            "---\n\n"
            "Hi [Reader],\n\n"
            "## [Opening Hook]\n[1-2 engaging paragraphs]\n\n"
            "## [Main Story / Feature]\n[3-4 paragraphs with insights]\n\n"
            "## Quick Takeaways\n- [3 bullet points]\n\n"
            "## Closing Thought\n[Personal, warm sign-off]\n\n"
            "— LEVI AI\n\n"
            "Total: 400-600 words. Conversational yet insightful."
        ),
        "user": "Write a {tone} newsletter about: {topic}",
    },
    "readme": {
        "max_tokens": 1500,
        "system": (
            "You are LEVI, a technical documentation expert. "
            "Write a professional README.md for a project about '{topic}'. "
            "Format:\n"
            "# [Project Name]\n\n"
            "> [One-line tagline]\n\n"
            "## Overview\n[What it is and why it exists — 2-3 sentences]\n\n"
            "## Features\n- [Bullet list of key features]\n\n"
            "## Quick Start\n```bash\n[Installation and run commands]\n```\n\n"
            "## Usage\n[Code example or usage instructions]\n\n"
            "## Configuration\n[Environment variables or config options]\n\n"
            "## Contributing\n[Brief contribution guide]\n\n"
            "## License\n[MIT / Apache 2.0 / etc.]\n"
            "Tone: {tone}. Be concise, scannable, and developer-friendly."
        ),
        "user": "Write a README for: {topic}",
    },
}


# ─────────────────────────────────────────────
# Available Tones
# ─────────────────────────────────────────────
TONES = [
    "inspiring", "philosophical", "poetic", "witty", "dramatic",
    "calm", "energetic", "dark", "humorous", "professional",
    "conversational", "academic", "stoic", "mystical",
]


# ─────────────────────────────────────────────
# Main Generation Function
# ─────────────────────────────────────────────
def generate_content(
    content_type: str,
    topic: str,
    tone: str = "inspiring",
    depth: str = "high",
    language: str = "English",
) -> dict:
    """
    Generate content of the specified type.

    Args:
        content_type: One of CONTENT_TEMPLATES keys.
        topic: The subject matter.
        tone: Emotional/stylistic tone.
        depth: 'low', 'medium', or 'high' — affects detail level.
        language: Output language (e.g. 'English', 'Spanish', 'Hindi').

    Returns:
        dict with 'content', 'type', 'topic', 'tone', 'word_count', 'language', 'streaming'.
    """
    if content_type not in CONTENT_TEMPLATES:
        return {
            "error": f"Unknown content type: '{content_type}'. "
                     f"Available: {list(CONTENT_TEMPLATES.keys())}"
        }

    template = CONTENT_TEMPLATES[content_type]
    tone = tone if tone in TONES else "inspiring"

    # Adjust max_tokens based on depth
    depth_multiplier = {"low": 0.5, "medium": 0.75, "high": 1.0}
    base_tokens = int(template["max_tokens"])
    max_tokens = int(base_tokens * depth_multiplier.get(depth, 1.0))
    
    # Dynamic Temperature mapping
    temp_map = {"poem": 0.92, "readme": 0.70, "story": 0.85, "essay": 0.75, "quote": 0.85}
    temperature = temp_map.get(content_type, 0.80)

    # Build prompts — inject language directive if non-English
    system_prompt = str(template["system"]).format(topic=topic, tone=tone)
    user_prompt = str(template["user"]).format(topic=topic, tone=tone)
    
    # Inject Tone Modifiers
    TONE_MODIFIERS = {
        "dark": "Use stark, visceral imagery and focus on the shadows of the human experience.",
        "humorous": "Be witty, clever, and use subtle irony or playful observations.",
        "bold": "Be uncompromising, direct, and authoritative in your assertions.",
        "intimate": "Speak as a close confidant, using personal, warm, and vulnerable language."
    }
    if tone in TONE_MODIFIERS:
        system_prompt += f"\n\nTone strict adherence: {TONE_MODIFIERS[tone]}"
        
    system_prompt += "\nCRITICAL ANTI-CLICHE RULE: Do not use the words 'profound', 'tapestry', 'cosmic dance', 'delve', 'testament', 'journey', or 'landscape'. Never start with pleasantries like 'Certainly' or 'Here is'."
    
    if language.lower() not in ("english", "en"):
        system_prompt += f" Write entirely in {language}."

    raw_content = _generate_via_groq(system_prompt, user_prompt, max_tokens, temperature)

    if not raw_content:
        content = f"[Content generation unavailable. Topic: {topic}, Type: {content_type}]"
    else:
        # Anti-cliché post-processing
        c_str: str = str(raw_content)
        for op in ["certainly", "great question", "here is", "sure!", "of course", "here's"]:
            if c_str.lower().startswith(op):
                start_idx: int = len(op)
                end_idx: int = len(c_str)
                c_str = c_str[start_idx:end_idx].lstrip(' \n,:-!')  # type: ignore
        content = c_str.replace("cosmic dance", "natural motion").replace("In conclusion,", "").strip()

    word_count = len(content.split())

    return {
        "content": content,
        "type": content_type,
        "topic": topic,
        "tone": tone,
        "word_count": word_count,
        "language": language,
        "streaming": False,  # Reserved for future streaming API support
    }


def _generate_via_groq(system_prompt: str, user_prompt: str, max_tokens: int, temperature: float = 0.8) -> Optional[str]:
    """Call Groq Llama3 for content generation."""
    try:
        import groq  # type: ignore
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            logger.warning("[ContentEngine] No GROQ_API_KEY set.")
            return None

        client = groq.Groq(api_key=api_key)
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"[ContentEngine] Groq generation failed: {e}")
        return None


# ─────────────────────────────────────────────
# Utility
# ─────────────────────────────────────────────
def get_available_types() -> list:
    """Return list of available content types."""
    return list(CONTENT_TEMPLATES.keys())


def get_available_tones() -> list:
    """Return list of available tones."""
    return TONES


# ─────────────────────────────────────────────
# Batch Generation
# ─────────────────────────────────────────────
def batch_generate(requests: list) -> list:
    """
    Generate multiple content pieces in one call.

    Args:
        requests: List of dicts, each with keys:
            - content_type (required)
            - topic (required)
            - tone (optional, default 'inspiring')
            - depth (optional, default 'high')
            - language (optional, default 'English')

    Returns:
        List of result dicts from generate_content().

    Example:
        batch_generate([
            {"content_type": "quote", "topic": "resilience"},
            {"content_type": "poem", "topic": "the ocean", "tone": "calm"},
        ])
    """
    results = []
    for req in requests:
        content_type = req.get("content_type", "")
        topic = req.get("topic", "")
        tone = req.get("tone", "inspiring")
        depth = req.get("depth", "high")
        language = req.get("language", "English")
        result = generate_content(content_type, topic, tone=tone, depth=depth, language=language)
        results.append(result)
    return results
