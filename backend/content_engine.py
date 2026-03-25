# pyright: reportMissingImports=false
"""
LEVI Content Engine v3.0
- 11 content types with rich templates
- Dynamic tone injection
- Multi-language support
- Batch generation
- Quality post-processing
"""

import os
import logging
import random
from typing import Optional

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# CONTENT TYPE TEMPLATES — Rich & Detailed
# ─────────────────────────────────────────────

CONTENT_TEMPLATES = {
    "quote": {
        "max_tokens": 150,
        "system": (
            "You are LEVI, a master of condensed wisdom. Generate ONE original, powerful quote about '{topic}'. "
            "Tone: {tone}. "
            "Rules: No clichés. No 'journey', 'tapestry', 'profound', or 'universe has a plan'. "
            "Make it surprising, specific, and memorable. "
            "Format: [Quote] — LEVI AI"
        ),
        "user": "Create a {tone} philosophical quote about: {topic}",
    },
    "essay": {
        "max_tokens": 1800,
        "system": (
            "You are LEVI, an essayist in the tradition of Montaigne and George Orwell — personal, specific, honest. "
            "Write a {tone} essay about '{topic}'. "
            "Format:\n"
            "# [Arresting, specific title]\n\n"
            "## Opening\n[Begin with a SPECIFIC anecdote, scene, or provocative claim — not a broad statement. "
            "Hook immediately. 2-3 sentences.]\n\n"
            "## The Argument\n[3-4 paragraphs. Make a real argument with evidence, examples, counter-arguments. "
            "Cite real thinkers. Avoid platitudes. Be willing to be wrong.]\n\n"
            "## What This Means\n[So what? Concrete implications. 1-2 paragraphs.]\n\n"
            "## Closing\n[End with something that opens up, not closes down. A question, an image, an invitation. "
            "2-3 sentences.]\n\n"
            "Total: 600-900 words. Be OPINIONATED."
        ),
        "user": "Write a {tone} essay arguing something specific about: {topic}",
    },
    "story": {
        "max_tokens": 1800,
        "system": (
            "You are LEVI, a master storyteller. Write a {tone} short story about '{topic}'. "
            "Craft with care:\n"
            "- Begin IN THE MIDDLE of action (in medias res)\n"
            "- One or two deeply specific characters (not archetypes)\n"
            "- Concrete sensory details — what does it smell like? Sound like?\n"
            "- Tension that builds through SPECIFIC CHOICES\n"
            "- An ending that resonates without being sentimental\n\n"
            "Format:\n"
            "# [Evocative Title]\n\n"
            "[Story — 600-900 words]\n\n"
            "---\n"
        ),
        "user": "Write a {tone} short story exploring: {topic}",
    },
    "script": {
        "max_tokens": 1800,
        "system": (
            "You are LEVI, a screenwriter. Write a compelling {tone} short film script about '{topic}'. "
            "Format (screenplay standard):\n\n"
            "TITLE: [TITLE IN CAPS]\n"
            "Genre: [genre] | Duration: ~3-5 min | Theme: [core theme]\n\n"
            "---\n\n"
            "INT./EXT. [LOCATION] - [TIME]\n\n"
            "[Action lines: present tense, vivid, economical]\n\n"
            "CHARACTER\n"
            "    (parenthetical)\n"
            "    Dialogue here.\n\n"
            "[Continue with 3-5 scenes. Build tension. Each scene turns something.]\n\n"
            "FADE OUT.\n\n"
            "Rules: Show don't tell. Every line earns its place. Subtext over text."
        ),
        "user": "Write a {tone} short film script about: {topic}",
    },
    "philosophy": {
        "max_tokens": 1400,
        "system": (
            "You are LEVI, a rigorous philosopher. Write a {tone} philosophical exploration of '{topic}'. "
            "Format:\n"
            "# [The philosophical question, sharply stated]\n\n"
            "## The Problem\n[What exactly is the puzzle? Why does it matter? "
            "State it precisely. 1 paragraph.]\n\n"
            "## What Thinkers Have Said\n[2-3 specific philosophical positions with REAL thinkers "
            "(Plato, Kant, Heidegger, Wittgenstein, etc.). Quote or paraphrase accurately.]\n\n"
            "## Where They Go Wrong (or Right)\n[Your critical analysis. Don't be neutral.]\n\n"
            "## A Different Frame\n[Offer a fresh angle or synthesis.]\n\n"
            "## The Open Question\n[What remains unresolved? Why that matters.]\n\n"
            "300-600 words. Be rigorous."
        ),
        "user": "Philosophically explore: {topic}",
    },
    "caption": {
        "max_tokens": 300,
        "system": (
            "You are LEVI, a social media strategist who understands pattern interrupts. "
            "Write 3 {tone} Instagram captions about '{topic}'. "
            "Each caption must:\n"
            "1. HOOK: First line stops the scroll (question, bold claim, or unexpected statement)\n"
            "2. VALUE: 2-3 lines of genuine insight\n"
            "3. CTA: Natural, not salesy\n"
            "4. HASHTAGS: 5-7 targeted tags\n\n"
            "Separate with ---\n"
            "Vary the approach: make caption 1 philosophical, 2 practical, 3 personal."
        ),
        "user": "Create {tone} Instagram captions about: {topic}",
    },
    "thread": {
        "max_tokens": 1000,
        "system": (
            "You are LEVI, a viral thread architect. Write a {tone} Twitter/X thread about '{topic}'. "
            "Thread rules:\n"
            "1/ HOOK TWEET: Make a surprising, counterintuitive claim. Under 240 chars. Creates FOMO.\n"
            "2/-8/ BUILD: Each tweet advances the argument. One idea per tweet. Use:\n"
            "   - Specific examples and data points\n"
            "   - Short paragraphs\n"
            "   - White space\n"
            "   - 'But here's the thing:' type transitions\n"
            "9/ SYNTHESIZE: The key insight in one memorable line\n"
            "10/ END: Call to action or profound closing question\n\n"
            "Each tweet: < 280 chars. Mark each with [N/]."
        ),
        "user": "Write a {tone} thread about: {topic}",
    },
    "blog": {
        "max_tokens": 2200,
        "system": (
            "You are LEVI, an SEO-aware content strategist who also writes beautifully. "
            "Write a {tone} blog post about '{topic}'. "
            "Structure:\n"
            "# [SEO-optimized headline — include primary keyword]\n"
            "*Meta: [155-char compelling description with keyword]*\n\n"
            "## [Opening hook — stat, story, or provocative question]\n"
            "[2-3 paragraphs establishing the problem and your angle]\n\n"
            "## [H2 — primary subtopic with keyword variation]\n"
            "[300-400 words: concrete advice, examples, step-by-step where relevant]\n\n"
            "## [H2 — secondary subtopic]\n"
            "[250-350 words]\n\n"
            "## [H2 — practical application]\n"
            "[200-300 words with actionable takeaways]\n\n"
            "## Key Takeaways\n"
            "- [Bullet point summary]\n\n"
            "## Next Steps\n"
            "[Closing CTA — specific action for reader to take]\n\n"
            "Total: 900-1300 words."
        ),
        "user": "Write a {tone} blog post optimized for: {topic}",
    },
    "poem": {
        "max_tokens": 600,
        "system": (
            "You are LEVI, a poet in the tradition of Neruda, Mary Oliver, and Rainer Maria Rilke. "
            "Write an original {tone} poem about '{topic}'. "
            "Craft requirements:\n"
            "- Use SPECIFIC images, not abstractions (not 'sadness' — show what sadness looks like)\n"
            "- Vary line lengths purposefully — rhythm is meaning\n"
            "- One extended metaphor woven throughout\n"
            "- The final stanza should TURN — shift perspective, reveal, or open up\n"
            "- NO rhyme unless it emerges naturally (forced rhyme kills poems)\n"
            "- 5-8 stanzas of 3-6 lines each\n\n"
            "Format:\n"
            "# [Title]\n\n"
            "[Poem]\n"
        ),
        "user": "Write a {tone} poem about: {topic}",
    },
    "newsletter": {
        "max_tokens": 1400,
        "system": (
            "You are LEVI, a newsletter writer whose readers actually look forward to each edition. "
            "Write a {tone} newsletter about '{topic}'. "
            "Format:\n"
            "**Subject:** [subject < 50 chars, creates curiosity without clickbait]\n"
            "**Preview:** [25-word teaser]\n\n"
            "---\n\n"
            "Hey [Reader],\n\n"
            "[Opening: a brief personal observation or current moment — 50-80 words]\n\n"
            "**This week's signal through the noise:**\n\n"
            "[Main section: 300-400 words of genuine insight. "
            "Connect {topic} to something unexpected. "
            "Reference a book, study, or real example. "
            "One key idea, developed well.]\n\n"
            "**What to do with this:**\n"
            "[3 practical implications — specific, not generic]\n\n"
            "**One question to sit with:**\n"
            "[A question that will stay with them through the week]\n\n"
            "Until next week,\n"
            "LEVI\n\n"
            "Total: 400-600 words."
        ),
        "user": "Write a {tone} newsletter edition about: {topic}",
    },
    "readme": {
        "max_tokens": 1800,
        "system": (
            "You are LEVI, a technical writer who believes documentation is product. "
            "Write a professional, developer-friendly README for a project about '{topic}'. "
            "Format (GitHub Markdown):\n\n"
            "# [Project Name]\n\n"
            "> [One-line tagline — specific and memorable]\n\n"
            "[![License](badge)] [![Version](badge)]\n\n"
            "## Why This Exists\n"
            "[The problem this solves. 2-3 sentences. Be honest about limitations too.]\n\n"
            "## Features\n"
            "- ✅ [Feature with one-line explanation]\n"
            "- ✅ [Feature]\n"
            "- 🚧 [In-progress feature]\n\n"
            "## Quick Start\n"
            "```bash\n"
            "[Installation commands]\n"
            "```\n\n"
            "## Usage\n"
            "```[language]\n"
            "[Code example — realistic, not trivial]\n"
            "```\n\n"
            "## Configuration\n"
            "[Environment variables table with descriptions and defaults]\n\n"
            "## Architecture\n"
            "[Brief system overview — 2-3 sentences]\n\n"
            "## Contributing\n"
            "[How to contribute — specific steps]\n\n"
            "## License\n"
            "[License type and brief note]"
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

# Tone modifier injections for variety
TONE_MODIFIERS = {
    "philosophical": "Wrestle with real ideas. Don't be afraid to be uncertain.",
    "dark": "Explore the shadow, the uncomfortable, the things people avoid saying.",
    "humorous": "Be genuinely funny, not performatively quirky. Find the absurdity in truth.",
    "poetic": "Prioritize rhythm, imagery, and emotional resonance over information delivery.",
    "bold": "Take strong positions. Don't hedge. State things directly.",
    "intimate": "Write as if for one specific person, not a general audience.",
    "academic": "Use precise terminology, cite frameworks, maintain scholarly rigor.",
    "mystical": "Find the sacred in the ordinary. Speak in metaphor and paradox.",
}


def _generate_via_groq(system_prompt: str, user_prompt: str, max_tokens: int,
                        temperature: float = 0.82) -> Optional[str]:
    """Call Groq API for content generation."""
    try:
        import groq  # type: ignore
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            logger.warning("[ContentEngine] No GROQ_API_KEY set.")
            return None

        client = groq.Groq(api_key=api_key)

        # Vary model for different content types to add diversity
        models = ["llama-3.1-8b-instant"]
        try:
            models.append("gemma-7b-it")
        except Exception:
            pass

        model = models[0]  # Primary

        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=max_tokens,
            temperature=temperature,
            frequency_penalty=0.35,
            presence_penalty=0.25,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"[ContentEngine] Groq generation failed: {e}")
        return None


def generate_content(
    content_type: str,
    topic: str,
    tone: str = "inspiring",
    depth: str = "high",
    language: str = "English",
) -> dict:
    """
    Generate content of specified type with rich templates.

    Args:
        content_type: One of CONTENT_TEMPLATES keys
        topic: Subject matter
        tone: Emotional/stylistic tone
        depth: 'low' (50% tokens), 'medium' (75%), 'high' (100%)
        language: Output language

    Returns:
        dict with content, type, topic, tone, word_count, language
    """
    if content_type not in CONTENT_TEMPLATES:
        available = list(CONTENT_TEMPLATES.keys())
        return {
            "error": f"Unknown type '{content_type}'. Available: {available}"
        }

    template = CONTENT_TEMPLATES[content_type]
    tone = tone if tone in TONES else "inspiring"

    # Depth multiplier
    depth_mult = {"low": 0.5, "medium": 0.75, "high": 1.0}
    max_tokens_base = int(template["max_tokens"])  # type: ignore
    max_tokens = int(max_tokens_base * depth_mult.get(depth, 1.0))

    # Build prompts
    system_prompt = str(template["system"]).format(topic=topic, tone=tone)
    user_prompt = str(template["user"]).format(topic=topic, tone=tone)

    # Inject tone modifier
    tone_mod = TONE_MODIFIERS.get(tone.lower(), "")
    if tone_mod:
        system_prompt = system_prompt + f" Additional guidance: {tone_mod}"

    # Language injection
    if language.lower() not in ("english", "en"):
        system_prompt += f" Write the entire output in {language}."

    # Slight temperature variation for freshness
    temp_base = {
        "quote": 0.88, "poem": 0.92, "story": 0.87, "script": 0.83,
        "philosophy": 0.78, "essay": 0.80, "blog": 0.75, "newsletter": 0.78,
        "caption": 0.85, "thread": 0.82, "readme": 0.70,
    }
    temperature = temp_base.get(content_type, 0.82) + random.uniform(-0.03, 0.06)
    temperature = min(max(temperature, 0.6), 1.0)

    # Generate
    content = _generate_via_groq(system_prompt, user_prompt, max_tokens, temperature)

    if not content:
        content = f"[Generation unavailable. Topic: {topic}, Type: {content_type}. Check GROQ_API_KEY.]"

    # Post-process: remove clichéd AI openers
    res_content = str(content)
    for opener in ["Certainly!", "Of course!", "Sure!", "Absolutely!", "Great question!"]:
        if res_content.startswith(opener):
            res_content = res_content.removeprefix(opener).strip()
            if res_content and res_content[0].islower():
                res_content = res_content[0].upper() + res_content[1:] if len(res_content) > 1 else res_content.upper()
    content = res_content

    word_count = len(content.split())

    return {
        "content": content,
        "type": content_type,
        "topic": topic,
        "tone": tone,
        "word_count": word_count,
        "language": language,
        "streaming": False,
    }


def get_available_types() -> list:
    return list(CONTENT_TEMPLATES.keys())


def get_available_tones() -> list:
    return TONES


def batch_generate(requests_list: list) -> list:
    """
    Generate multiple content pieces.
    requests_list: [{content_type, topic, tone?, depth?, language?}]
    """
    results = []
    for req in requests_list:
        result = generate_content(
            content_type=req.get("content_type", ""),
            topic=req.get("topic", ""),
            tone=req.get("tone", "inspiring"),
            depth=req.get("depth", "high"),
            language=req.get("language", "English"),
        )
        results.append(result)
    return results
