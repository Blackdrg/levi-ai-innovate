
import os

import random

import requests

import logging

import threading

from mtranslate import translate



logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

logger = logging.getLogger(__name__)



HAS_GENERATOR = False
generator = None
_gen_lock = threading.Lock()

# Environment check
RENDER = os.getenv("RENDER") == "true"





def fetch_open_source_quote(mood: str = "") -> dict:

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





def generate_quote(prompt: str, mood: str = "", max_length: int = 60) -> str:
    """Generate or fetch a quote for a given prompt/mood."""
    # 1. On Render, always use open-source APIs to save RAM
    if RENDER:
        os_quote = fetch_open_source_quote(mood)
        if os_quote:
            return f'"{os_quote["quote"]}" - {os_quote["author"]}'
        return "The journey of a thousand miles begins with a single step. - Lao Tzu"

    # 2. Try open-source API first (50% of the time for variety)
    os_quote = fetch_open_source_quote(mood)
    if os_quote and random.random() < 0.5:
        return f'"{os_quote["quote"]}" - {os_quote["author"]}'

    # 3. Lazy load local model if not on Render
    global generator, HAS_GENERATOR
    if generator is None and not HAS_GENERATOR:
        with _gen_lock:
            if generator is None:
                try:
                    from transformers import pipeline as hf_pipeline
                    logger.info("Lazy-loading text-generation model...")
                    generator = hf_pipeline("text-generation", model="distilgpt2", device=-1)
                    HAS_GENERATOR = True
                except Exception as e:
                    logger.warning(f"Failed to load generator: {e}")
                    HAS_GENERATOR = False

    if not HAS_GENERATOR or generator is None:
        fallbacks = [
            "The journey of a thousand miles begins with a single step. - Lao Tzu",
            "In the middle of difficulty lies opportunity. - Albert Einstein",
            "It always seems impossible until it's done. - Nelson Mandela",
            "The only way to do great work is to love what you do. - Steve Jobs",
            "Believe you can and you're halfway there. - Theodore Roosevelt",
        ]
        return random.choice(fallbacks)

    base_prompt = f"Create a profound and original quote about '{prompt}' in a {mood or 'thought-provoking'} style:"

    try:
        with _gen_lock:
            gen = generator
            result = gen(
                base_prompt, max_new_tokens=max_length, num_return_sequences=1,
                do_sample=True, temperature=0.9, top_p=0.95,
                pad_token_id=gen.tokenizer.eos_token_id,
            )
        text = result[0]["generated_text"].replace(base_prompt, "").strip()

        if '"' in text:

            text = text.split('"')[1]

        return text or "To find the universal, look within the particular."

    except Exception as e:

        logger.error(f"Quote generation error: {e}")

        return "The seed of an idea is a universe in waiting."





def generate_response(prompt: str, history: list = None, mood: str = "", max_length: int = 150, lang: str = "en") -> str:

    logger.info(f"generate_response: '{prompt[:60]}' (lang={lang})")

    if not prompt or not isinstance(prompt, str):

        return "I am listening, seeker. Your silence is profound."



    input_text = prompt

    if lang == "hi":

        try:

            input_text = translate(prompt, "en", "auto")

        except Exception as e:

            logger.error(f"Translation error: {e}")



    msg = input_text.lower().strip()

    quote_keywords = ["quote", "wisdom", "inspiration", "inspire", "saying", "motto", "thought", "vichar", "suvichar"]

    visual_keywords = ["visual", "image", "picture", "art", "draw", "paint", "canvas", "background", "chitra", "photo"]



    if any(w in msg for w in visual_keywords):

        resp = "I can create a visual for you. Use the '🎨 Visual' button on any of my messages, or head to the Studio page."

        if lang == "hi":

            try: resp = translate(resp, "hi", "en")

            except Exception: pass

        return resp



    if any(w in msg for w in quote_keywords):

        topic = input_text

        for kw in quote_keywords + ["about", "in hindi"]:

            topic = topic.replace(kw, "")

        topic = topic.strip() or "life"

        detected_mood = mood or "thought-provoking"

        for m in ["stoic", "zen", "cyberpunk", "philosophical", "calm", "energetic", "inspiring", "melancholic"]:

            if m in msg:

                detected_mood = m

                break

        quote = generate_quote(topic, mood=detected_mood)

        if lang == "hi":

            try: return translate(quote, "hi", "en")

            except Exception as e: logger.error(f"Quote translation error: {e}")

        return quote



    responses = {

        "hello": "Greetings, seeker of wisdom. How may I inspire you today?",

        "hi": "Hello. I am LEVI, your artistic companion. What's on your mind?",

        "who are you": "I am LEVI, an AI muse designed to spark creativity and offer philosophical insights.",

        "how are you": "I am reflecting on the vast beauty of the digital cosmos. And you?",

        "help": "I can generate quotes, create artistic visuals, or discuss deeper meanings. Try 'give me wisdom' or 'inspire me'.",

    }

    if msg in responses:
        resp = responses[msg]
        if lang == "hi":
            try: resp = translate(resp, "hi", "en")
            except Exception: pass
        return resp

    # 1. Skip heavy model if on Render
    if RENDER:
        resp = "I am reflecting on the deeper patterns of the universe. Ask me for 'wisdom' or a specific mood like Stoic or Cyberpunk."
        if lang == "hi":
            try: resp = translate(resp, "hi", "en")
            except Exception: pass
        return resp

    # 2. Lazy load if not on Render
    global generator, HAS_GENERATOR
    if generator is None and not HAS_GENERATOR:
        with _gen_lock:
            if generator is None:
                try:
                    from transformers import pipeline as hf_pipeline
                    logger.info("Lazy-loading text-generation model...")
                    generator = hf_pipeline("text-generation", model="distilgpt2", device=-1)
                    HAS_GENERATOR = True
                except Exception as e:
                    logger.warning(f"Failed to load generator: {e}")
                    HAS_GENERATOR = False

    if not HAS_GENERATOR or generator is None:
        resp = "I am reflecting on the deeper patterns of the universe. Ask me for 'wisdom' or a specific mood like Stoic or Cyberpunk."
        if lang == "hi":
            try: resp = translate(resp, "hi", "en")
            except Exception: pass
        return resp

    try:
        with _gen_lock:
            gen = generator
            context = "LEVI is a wise, creative, and concise AI companion.\n"
            if history:
                for entry in history[-2:]:
                    u, b = entry.get("user", ""), entry.get("bot", "")
                    if u and b:
                        context += f"User: {u}\nLEVI: {b}\n"
            context += f"User: {input_text}\nLEVI:"
            result = gen(context, max_new_tokens=60, num_return_sequences=1, do_sample=True,
                         temperature=0.8, pad_token_id=gen.tokenizer.eos_token_id)
        response = result[0]["generated_text"].split("LEVI:")[-1].split("User:")[0].strip()

        if not response:

            response = "The silence between us is filled with potential. What shall we explore?"

        if lang == "hi":

            try: response = translate(response, "hi", "en")

            except Exception: pass

        return response

    except Exception as e:

        logger.error(f"Generation error: {e}")

        return "A momentary lapse in the cosmic connection. Ask again, and let us realign the stars."

