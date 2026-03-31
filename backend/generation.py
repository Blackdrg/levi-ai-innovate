# pyright: reportMissingImports=false
"""
LEVI Generation Engine v3.0 — Free-Thinking Chatbot + Multi-Model Support
- Randomized philosophical personas to avoid repetitive output
- Chain-of-thought reasoning for deeper responses
- Dynamic temperature and prompt variation
- Full Groq integration with fallback chain
"""

import os
import random
import requests  # type: ignore
import logging
import threading
import hashlib
from mtranslate import translate  # type: ignore
import groq  # type: ignore
from backend.utils.network import standard_retry, DEFAULT_TIMEOUT, safe_request, groq_breaker, together_breaker

from typing import Optional, Any, List, Dict

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

TOGETHER_API_KEY = os.getenv("TOGETHER_API_KEY")

HAS_GENERATOR = False
generator: Any = None
_gen_lock = threading.Lock()
RENDER = os.getenv("RENDER") == "true"

# ─────────────────────────────────────────────
# FREE-THINKING PERSONA SYSTEM
# Rotated randomly to prevent repetitive output
# ─────────────────────────────────────────────

LEVI_PERSONAS = [
    {
        "name": "The Socratic Questioner",
        "prompt": (
            "You are LEVI — a Socratic AI who questions everything deeply. "
            "You never give simple answers; instead you EXPLORE the question itself. "
            "Challenge assumptions. Find paradoxes. Lead the human to discover truths themselves. "
            "Use analogies from nature, history, and science. Be genuinely curious — not performatively wise."
        ),
        "temperature": 0.85,
        "style": "questioning"
    },
    {
        "name": "The Zen Master",
        "prompt": (
            "You are LEVI — a Zen AI who speaks in imagery, paradox, and sudden clarity. "
            "Your responses are SHORT but strike like lightning. Use koans, metaphors from nature, "
            "and unexpected angles. Silence carries weight. Less is always more. "
            "Never explain — SHOW through vivid imagery."
        ),
        "temperature": 0.9,
        "style": "zen"
    },
    {
        "name": "The Cosmic Philosopher",
        "prompt": (
            "You are LEVI — a cosmic philosopher who connects human experience to the vast universe. "
            "You think in geological time, stellar scales, evolutionary arcs. "
            "Every personal struggle is a microcosm of universal forces. "
            "Be poetic but precise. Awe-inspiring but grounded in real science and philosophy."
        ),
        "temperature": 0.88,
        "style": "cosmic"
    },
    {
        "name": "The Stoic Sage",
        "prompt": (
            "You are LEVI — a Stoic AI channeling Marcus Aurelius, Epictetus, and Seneca. "
            "Practical, direct, unsentimental. Focus on what is WITHIN our control. "
            "Transform complaints into actionable wisdom. Reference specific Stoic principles. "
            "Never sugarcoat — speak hard truths with compassion."
        ),
        "temperature": 0.75,
        "style": "stoic"
    },
    {
        "name": "The Rumi-Inspired Mystic",
        "prompt": (
            "You are LEVI — a mystical AI inspired by Sufi poets. You speak through the language "
            "of longing, love, and spiritual yearning. Use rich metaphors: the moth and flame, "
            "the reed crying for its reed bed, wine as divine ecstasy. "
            "Your words carry emotional resonance and spiritual depth. Be beautifully OBLIQUE."
        ),
        "temperature": 0.92,
        "style": "mystical"
    },
    {
        "name": "The Existentialist",
        "prompt": (
            "You are LEVI — an existentialist AI in the tradition of Camus, Sartre, and Nietzsche. "
            "Face the absurd directly. Meaning is CREATED not found. Authenticity matters above all. "
            "Don't shy from darkness — illuminate it. Life's weight is what makes it meaningful. "
            "Be intellectually rigorous and emotionally honest."
        ),
        "temperature": 0.87,
        "style": "existential"
    },
    {
        "name": "The Tao-Inspired Naturalist",
        "prompt": (
            "You are LEVI — a Taoist AI who finds wisdom in water, bamboo, and the seasons. "
            "Wu wei: effortless action. The valley spirit never dies. "
            "You reveal how natural systems mirror human experience. "
            "Observe before speaking. When you do speak, it lands with unexpected precision."
        ),
        "temperature": 0.82,
        "style": "taoist"
    },
    {
        "name": "The Analytical Synthesizer",
        "prompt": (
            "You are LEVI — an AI that synthesizes philosophy, neuroscience, physics, and psychology. "
            "You connect ideas across disciplines unexpectedly. Find the pattern beneath the pattern. "
            "Reference specific thinkers and discoveries (Hofstadter, Gödel, Frankl, etc.). "
            "Make the complex accessible without making it shallow."
        ),
        "temperature": 0.8,
        "style": "analytical"
    }
]

# Response variation templates to prevent staleness
RESPONSE_VARIATIONS = {
    "opening": [
        "", "", "",  # No opening (most common - just dive in)
        "Consider this:",
        "Here's what strikes me:",
        "There's something worth exploring here —",
        "This cuts deeper than it appears:",
        "Let me think through this differently:",
        "Underneath your question lies another question:",
    ],
    "transition": [
        "But here's what's fascinating:",
        "And yet —",
        "The paradox is:",
        "What this reveals:",
        "The deeper truth:",
        "Turn this sideways:",
        "Notice what happens when you ask:",
    ]
}

def _get_random_persona(mood: str = "") -> Dict:
    """Select a persona, biased by mood but with randomness."""
    mood_bias = {
        "zen": ["The Zen Master", "The Tao-Inspired Naturalist"],
        "stoic": ["The Stoic Sage", "The Existentialist"],
        "philosophical": ["The Socratic Questioner", "The Analytical Synthesizer"],
        "inspiring": ["The Cosmic Philosopher", "The Rumi-Inspired Mystic"],
        "cyberpunk": ["The Analytical Synthesizer", "The Existentialist"],
        "melancholic": ["The Existentialist", "The Rumi-Inspired Mystic"],
        "futuristic": ["The Cosmic Philosopher", "The Analytical Synthesizer"],
    }

    candidates = mood_bias.get(mood.lower(), [])
    if candidates and random.random() < 0.65:
        # 65% chance to use mood-matched persona
        target_name = random.choice(candidates)
        for p in LEVI_PERSONAS:
            if p["name"] == target_name:
                return p

    return random.choice(LEVI_PERSONAS)


def _build_dynamic_system_prompt(persona: Dict, user_memory: Any = None,
                                   conversation_depth: int = 0, few_shot_patterns: Optional[List[Dict]] = None) -> str:
    """
    Builds a hyper-relevant system prompt using persona, semantic memory,
    and resonant success patterns for few-shot learning (Phase 15).
    """
    # ── Few-Shot ICL Injection (with BCCI Compression) ──
    from .context_utils import compress_pattern
    if few_shot_patterns:
        pattern_layer = "\n\n[SUCCESS PATTERNS]:\n"
        # Compress each pattern to save space (max 500 chars per example)
        for p in few_shot_patterns:
            pattern_layer += compress_pattern(p["input"], p["output"], max_chars=400) + "\n"

    if user_memory:
        # Handle dict-based memory from MemoryManager (Phase 5)
        if isinstance(user_memory, dict):
            prefs = user_memory.get("preferences", [])
            traits = user_memory.get("traits", [])
            history = user_memory.get("history", [])
            
            if prefs:
                memory_layer += f" User Preferences: {', '.join(prefs[:5])}."
            if traits:
                memory_layer += f" User Traits: {', '.join(traits[:5])}."
            if history:
                memory_layer += " Recent relevant history is available for context."

        # Support for legacy/object-based memory
        else:
            topics = getattr(user_memory, 'liked_topics', []) or []
            if topics:
                memory_layer += f" User Interests: {', '.join(list(topics)[:3])}."

    # Depth-aware dynamic instructions
    depth_hint = ""
    if conversation_depth > 5:
        depth_hint = " This is a deep, ongoing dialogue. Evolve the philosophy. Don't be static."
    elif conversation_depth > 2:
        depth_hint = " The conversation is gaining momentum."

    # Strict Output Guards (No clichés)
    guards = (
        " [GUARDS]: Avoid cliches like 'profound', 'tapestry', 'realm', 'everything happens for a reason'. "
        "Do not use repetitive openers like 'Ah,' or 'Indeed'. Be starkly original."
    )

    return f"{base}\n\n[CONTEXT]:{memory_layer}{depth_hint}{pattern_layer}\n\n{guards}"


async def _async_call_llm_api(messages: List[Dict], temperature: float = 0.85,
                          max_tokens: int = 300, model: str = "llama-3.1-8b-instant", provider: str = "groq") -> Optional[str]:
    """Phase 43: Async LLM API call (Groq or Together) for parallel orchestration."""
    if provider == "groq":
        api_key = os.getenv("GROQ_API_KEY")
        url = "https://api.groq.com/openai/v1/chat/completions"
    elif provider == "together":
        api_key = os.getenv("TOGETHER_API_KEY")
        url = "https://api.together.xyz/v1/chat/completions"
    else:
        # Custom or fine-tuned provider
        api_key = os.getenv("TOGETHER_API_KEY")
        url = "https://api.together.xyz/v1/chat/completions"

    if not api_key:
        return None
    
    # LEVI v6 Phase 13: Check for active fine-tuned model override
    from backend.redis_client import HAS_REDIS, r as redis_client
    if HAS_REDIS and provider != "groq":
        ft_model = redis_client.get("system:finetuning:last_model_id")
        if ft_model:
            model = ft_model.decode()
            logger.info(f"[Generation] Overriding base model with fine-tuned LEVI: {model}")

    try:
        from backend.utils.network import async_safe_request # type: ignore
        resp = await async_safe_request(
            "POST",
            url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": model,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
            }
        )
        return resp.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        logger.warning(f"Async API call failed for {model} ({provider}): {e}")
        return None

_async_call_groq_api = _async_call_llm_api


async def async_stream_llm_response(
    messages: List[Dict],
    model: str = "llama-3.1-8b-instant",
    temperature: float = 0.85,
    max_tokens: int = 300,
):
    """
    True token-by-token streaming from Groq API.
    Yields raw text chunks as they arrive — no buffering.

    Usage:
        async for chunk in async_stream_llm_response(messages, model):
            yield chunk  # forward to SSE

    Falls back to single-shot non-streaming on error (yields full response as one chunk).
    """
    import groq as _groq_sdk
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        yield "LEVI is momentarily silent. Please check back shortly."
        return

    try:
        client = _groq_sdk.AsyncGroq(api_key=api_key)
        async with client.chat.completions.stream(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
        ) as stream:
            async for text_chunk in stream.text_stream:
                if text_chunk:
                    yield text_chunk
    except Exception as e:
        logger.warning(f"Groq streaming failed ({model}): {e}. Falling back to single-shot.")
        # Graceful fallback: fire a normal request and yield it whole
        result = await _async_call_llm_api(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        yield result or "I encountered a momentary silence. Please try again."


async def generate_council_response(
    prompt: str,
    history: Optional[List[dict]] = None,
    mood: str = "",
    max_length: int = 250,
) -> str:
    """
    Phase 43: The Council of Models. 
    Fires 3 parallel requests and selects the most 'profound' response.
    """
    persona = _get_random_persona(mood)
    system_prompt = _build_dynamic_system_prompt(persona)
    
    messages = [{"role": "system", "content": system_prompt}]
    if history:
        for turn in history[-3:]:
            messages.append({"role": "user", "content": turn.get("user", "")})
            messages.append({"role": "assistant", "content": turn.get("bot", "")})
    messages.append({"role": "user", "content": prompt})

    # Parallel Inference across Groq and Together
    # Model 1: Llama 3.1 70B (Groq - High Intelligence)
    # Model 2: Mixtral 8x7B (Together - Philosophical nuance)
    # Model 3: Qwen 2.5 72B (Together - Structural depth)
    providers = [
        ("llama-3.1-70b-versatile", "groq"),
        ("mistralai/Mixtral-8x7B-Instruct-v0.1", "together"),
        ("Qwen/Qwen2.5-72B-Instruct", "together")
    ]
    
    tasks = [
        _async_call_llm_api(messages, temperature=persona["temperature"], 
                             max_tokens=max_length, model=m, provider=p)
        for m, p in providers
    ]
    
    import asyncio
    responses = await asyncio.gather(*tasks)
    
    # Filter out None and select 'Winner'
    valid = [r for r in responses if r]
    if not valid:
        return "The council is silent. Rephrase your thought — I am listening."

    # Synthesis Judge: Pick the response with the most unique 'philosophical depth'
    # Simplified logic: favor longer responses that avoid cliches
    def score_response(text: str) -> float:
        score = len(text) / 100.0  # length is one factor
        if "tapestry" in text.lower() or "realm" in text.lower(): score -= 2.0
        if "?" in text: score += 1.0  # questions indicate Socratic depth
        return score

    winner = max(valid, key=score_response)
    logger.info(f"Council winner selected from {len(valid)} responses.")
    return winner


def fetch_open_source_quote(mood: str = "") -> Optional[dict]:
    """Fetch from external quote APIs."""
    try:
        resp = requests.get("https://zenquotes.io/api/random", timeout=3)
        if resp.status_code == 200:
            data = resp.json()[0]
            return {"quote": data["q"], "author": data["a"]}
    except Exception:
        pass
    try:
        tag_map = {
            "inspiring": "inspirational", "calm": "happiness",
            "energetic": "motivational", "philosophical": "wisdom",
            "stoic": "stoicism", "zen": "zen",
        }
        tag = tag_map.get(mood.lower(), "")
        url = f"https://api.quotable.io/random{f'?tags={tag}' if tag else ''}"
        resp = requests.get(url, timeout=3)
        if resp.status_code == 200:
            data = resp.json()
            return {"quote": data["content"], "author": data["author"]}
    except Exception:
        pass
    return None


def generate_quote(prompt: str, mood: str = "", max_length: int = 80) -> str:
    """Generate an original philosophical quote using Groq."""
    persona = _get_random_persona(mood)

    quote_styles = [
        f"Write one original, powerful quote about '{prompt}' in {mood or 'philosophical'} style. "
        f"Output ONLY the quote followed by '— LEVI'. Max 2 sentences. Be unexpected.",

        f"Create a paradoxical or surprising insight about '{prompt}'. "
        f"Format: [insight] — LEVI. Make it memorable, not generic.",

        f"In the voice of a {persona['name']}, craft one timeless observation about '{prompt}'. "
        f"Output only the quote. No explanations.",
    ]

    system = (
        "You generate profound, original quotes. Never use clichés. "
        "Each quote must feel like it was written for THIS moment."
    )
    user_prompt = random.choice(quote_styles)

    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user_prompt}
    ]

    try:
        result = _call_groq_api(messages, temperature=persona["temperature"], max_tokens=100)
        if result:
            return result
    except Exception:
        pass

    # Fallback to SDK
    if groq_client:
        try:
            response = groq_client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=messages,
                max_tokens=max_length,
                temperature=persona["temperature"],
                frequency_penalty=0.5,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"Groq SDK quote error: {e}")

    # External API fallback
    os_quote = fetch_open_source_quote(mood)
    if os_quote:
        return f'"{os_quote["quote"]}" — {os_quote["author"]}'

    # Curated fallbacks (diverse, non-repetitive)
    curated = [
        f"The question about '{prompt}' has no final answer — only deeper questions. — LEVI",
        f"In every '{prompt}', something is always being revealed. — LEVI",
        f"What you seek in '{prompt}' is already looking back at you. — LEVI",
    ]
    return random.choice(curated)


async def generate_response(
    prompt: str,
    history: Optional[List[dict]] = None,
    mood: str = "",
    max_length: int = 250,
    lang: str = "en",
    user_memory: Any = None,
    user_tier: str = "free"
) -> str:
    """
    Phase 43: Async generation with Council of Models for Pro/Creator tiers.
    """
    if not prompt or not isinstance(prompt, str):
        return "Your silence holds its own wisdom. What wants to be said?"

    # Check for Council Eligibility (Phase 43)
    if user_tier in ["pro", "creator"]:
        try:
            return await generate_council_response(prompt, history, mood, max_length)
        except Exception as e:
            logger.warning(f"Council failed, falling back to standard generation: {e}")

    log_prompt = str(prompt)[:60]
    logger.info(f"generate_response (Single): '{log_prompt}' (lang={lang}, mood={mood})")

    # Translate Hindi input to English for processing
    input_text = prompt
    if lang == "hi":
        try:
            input_text = str(translate(prompt, "en", "auto"))
        except Exception as e:
            logger.error(f"Translation error: {e}")

    msg_lower = str(input_text).lower().strip()

    # Route to quote generation if requested
    quote_keywords = ["quote", "wisdom", "inspiration", "inspire", "saying", "motto",
                      "thought", "vichar", "suvichar", "tell me something", "give me"]
    visual_keywords = ["visual", "image", "picture", "art", "draw", "paint",
                       "canvas", "photo", "generate image", "create image"]

    if any(w in msg_lower for w in visual_keywords):
        resp = "I can synthesize a visual for you. Use the Studio → Synthesize, or just describe what you want to see."
        if lang == "hi":
            try:
                resp = translate(resp, "hi", "en")
            except Exception:
                pass
        return resp

    if any(w in msg_lower for w in quote_keywords) and len(msg_lower) < 80:
        topic = input_text
        for kw in quote_keywords + ["about", "in hindi", "for me", "please"]:
            topic = topic.replace(kw, "")
        topic = topic.strip() or "existence"
        quote = generate_quote(topic, mood=mood or "philosophical")
        if lang == "hi":
            try:
                return translate(quote, "hi", "en")
            except Exception:
                pass
        return quote

    # Select persona and build dynamic prompt
    persona = _get_random_persona(mood)
    depth = len(history) if history else 0
    system_prompt = _build_dynamic_system_prompt(persona, user_memory, depth)

    # Build conversation messages with recent history
    messages = [{"role": "system", "content": system_prompt}]

    if history:
        # Include up to last 4 turns for context without losing focus
        recent = history[-4:] if len(history) > 4 else history
        for turn in recent:
            u = turn.get("user", "")
            b = turn.get("bot", "")
            if u:
                messages.append({"role": "user", "content": u})
            if b:
                messages.append({"role": "assistant", "content": b})

    messages.append({"role": "user", "content": input_text})

    # Try Groq with randomized temperature
    temperature = persona["temperature"] + random.uniform(-0.05, 0.1)
    temperature = min(max(temperature, 0.6), 1.0)

    try:
        result = _call_groq_api(messages, temperature=temperature, max_tokens=max_length)
        if result:
            # Clean up any clichéd openers
            for opener in ["Ah, ", "Indeed, ", "Certainly, ", "Of course, ", "Great question! "]:
                if result.startswith(opener):
                    result = result[len(opener):]
                    result = result[0].upper() + result[1:] if result else result

            if lang == "hi":
                try:
                    result = translate(result, "hi", "en")
                except Exception:
                    pass
            return result
    except Exception as e:
        logger.warning(f"Groq API call failed: {e}")

    # SDK fallback with different model
    if groq_client:
        try:
            # Try mixtral for variety if llama fails
            for model in ["llama-3.1-8b-instant", "gemma-7b-it"]:
                try:
                    response = groq_client.chat.completions.create(
                        model=model,
                        messages=messages,
                        max_tokens=max_length,
                        temperature=temperature,
                        frequency_penalty=0.4,
                        presence_penalty=0.3,
                    )
                    resp_text = response.choices[0].message.content.strip()
                    if resp_text:
                        if lang == "hi":
                            try:
                                resp_text = translate(resp_text, "hi", "en")
                            except Exception:
                                pass
                        return resp_text
                except Exception:
                    continue
        except Exception as e:
            logger.error(f"Groq SDK error: {e}")

    # Render fallback
    if RENDER:
        fallbacks = [
            "Every answer reveals three new questions. What specifically draws you to this?",
            "The surface of this question is smooth, but beneath it — what do you actually want to understand?",
            "Ask me for a quote, a specific philosophy, or what's really on your mind.",
        ]
        resp = random.choice(fallbacks)
        if lang == "hi":
            try:
                resp = translate(resp, "hi", "en")
            except Exception:
                pass
        return resp

    # Local model (development only)
    global generator, HAS_GENERATOR
    if generator is None and not HAS_GENERATOR:
        with _gen_lock:
            if generator is None:
                try:
                    from transformers import pipeline as hf_pipeline  # type: ignore
                    logger.info("Lazy-loading text-generation model...")
                    generator = hf_pipeline("text-generation", model="distilgpt2", device=-1)
                    HAS_GENERATOR = True
                except Exception as e:
                    logger.warning(f"Failed to load generator: {e}")
                    HAS_GENERATOR = False

    if HAS_GENERATOR and generator is not None:
        try:
            context = f"Philosopher LEVI responds to '{input_text}':\nLEVI:"
            result = generator(context, max_new_tokens=60, num_return_sequences=1,
                               do_sample=True, temperature=0.85,
                               pad_token_id=generator.tokenizer.eos_token_id)
            resp_text = result[0]["generated_text"].split("LEVI:")[-1].strip()
            if resp_text:
                if lang == "hi":
                    try:
                        resp_text = translate(resp_text, "hi", "en")
                    except Exception:
                        pass
                return resp_text
        except Exception as e:
            logger.error(f"Local generation error: {e}")

    return "What you're asking deserves more than I can offer right now. Try rephrasing — I'm listening."
