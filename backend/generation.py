import os
import random
import requests
from mtranslate import translate

try:
    from transformers import pipeline
    generator = pipeline('text-generation', model='distilgpt2', device=-1)  # CPU
    HAS_GENERATOR = True
except Exception as e:
    print(f"Warning: Failed to load text-generation model: {e}")
    HAS_GENERATOR = False


import logging

logging.basicConfig(level=logging.INFO)

def generate_response(prompt: str, history: list = None, mood: str = "", max_length: int = 150, lang: str = "en") -> str:
    """
    Generates a contextual and persona-driven response, deciding whether to generate a quote or a conversational reply.
    """
    logging.info(f"Generating response for prompt: '{prompt}' (lang: {lang})")
    
    # 1. Translate prompt to English if it's in Hindi for intent detection
    input_text = prompt
    if lang == "hi":
        try:
            input_text = translate(prompt, 'en', 'auto')
            logging.info(f"Translated input to English: {input_text}")
        except Exception as e:
            logging.error(f"Translation error: {e}")
    
    msg = input_text.lower().strip()
    logging.info(f"Normalized msg: '{msg}'")
    # 1. Intent Detection: Check if the user is asking for a quote or a visual.
    quote_keywords = ["quote", "wisdom", "inspiration", "inspire", "saying", "motto", "thought", "wisdom", "vichar", "suvichar"]
    visual_keywords = ["visual", "image", "picture", "art", "draw", "paint", "canvas", "background", "chitra", "photo"]
    
    is_quote_request = any(word in msg for word in quote_keywords)
    is_visual_request = any(word in msg for word in visual_keywords)
    
    if is_visual_request:
        logging.info("Intent: Visual generation request")
        resp = "I can certainly create a visual for you. Simply ask for a 'quote' first, or use the 'Visual' button on any of my previous messages to see it brought to life."
        if lang == "hi":
            try:
                resp = translate(resp, 'hi', 'en')
            except: pass
        return resp

    if is_quote_request:
        logging.info("Intent: Quote generation")
        # Extract topic from the prompt, or use a general theme
        topic = input_text.replace("quote", "").replace("about", "").replace("in hindi", "").strip()
        if not topic or topic in quote_keywords:
            topic = "life"
        
        # Determine mood from prompt or fallback to a default
        detected_mood = mood or "thought-provoking"
        for m in ["stoic", "zen", "cyberpunk", "philosophical", "calm", "energetic"]:
            if m in msg:
                detected_mood = m
                break
        
        # Generate a quote using the specialized function
        quote = generate_quote(topic, mood=detected_mood)
        
        # Translate to Hindi if needed
        if lang == "hi":
            try:
                logging.info(f"Translating quote to Hindi: {quote}")
                translated_quote = translate(quote, 'hi', 'en')
                logging.info(f"Translated quote result: {translated_quote}")
                return translated_quote
            except Exception as e:
                logging.error(f"Quote translation error: {e}")
        return quote

    # 2. Conversational Fallback
    logging.info("Intent: Conversational response")
    
    # Predefined responses for common inputs to bypass buggy model
    responses = {
        "hello": "Greetings, seeker of wisdom. How may I inspire you today?",
        "hi": "Hello. I am LEVI, your artistic companion. What's on your mind?",
        "who are you": "I am LEVI, an AI muse designed to spark your creativity and offer philosophical insights.",
        "how are you": "I am reflecting on the vast beauty of the digital cosmos. And you?",
        "help": "I can generate quotes, create artistic visuals, or just discuss the deeper meaning of things. Try asking for 'wisdom' or a 'cyberpunk quote'."
    }
    
    if msg in responses:
        resp = responses[msg]
        if lang == "hi":
            try:
                resp = translate(resp, 'hi', 'en')
            except: pass
        return resp

    # Construct context for the model
    context = (
        "LEVI is a wise, creative, and brief AI. "
        "User: Hello\nLEVI: Greetings. How can I inspire you today?\n"
    )

    if history:
        for entry in history[-2:]:
            u = entry.get('user', '')
            b = entry.get('bot', '')
            if u and b:
                context += f"User: {u}\nLEVI: {b}\n"
    
    context += f"User: {input_text}\nLEVI:"

    if not HAS_GENERATOR:
        logging.warning("Generator model not available. Returning fallback response.")
        resp = "I am currently reflecting on the deeper patterns of the universe. Ask me for 'wisdom' or a specific 'mood' like Stoic or Cyberpunk, and I shall provide a spark for your journey."
        if lang == "hi":
            try:
                resp = translate(resp, 'hi', 'en')
            except: pass
        return resp

    logging.info(f"Generating with context: {context}")
    try:
        logging.info(f"Full Prompt to Model: {context}")
        result = generator(
            context,
            max_new_tokens=max_length,
            num_return_sequences=1,
            do_sample=True,
            temperature=0.7,
            top_k=50,
            top_p=0.9,
            repetition_penalty=1.2,
            no_repeat_ngram_size=2,
            pad_token_id=generator.tokenizer.eos_token_id
        )
        
        response = result[0]['generated_text']
        logging.info(f"Raw generated response: {response}")
        response = response.split("LEVI:")[-1].strip()
        response = response.split("User:")[0].strip()
        
        if not response:
            logging.warning("Generated response is empty. Returning fallback.")
            response = "Your words resonate with the silence of the cosmos. What more can we explore together?"
            if lang == "hi":
                try:
                    response = translate(response, 'hi', 'en')
                except: pass
            return response
            
        if lang == "hi":
            try:
                response = translate(response, 'hi', 'en')
            except: pass
        return response

    except Exception as e:
        logging.error(f"Generation error: {e}")
        resp = "A momentary lapse in the cosmic connection. Ask again, and let us realign the stars."
        if lang == "hi":
            try:
                resp = translate(resp, 'hi', 'en')
            except: pass
        return resp



def fetch_open_source_quote(mood: str = "") -> dict:
    """Fetches a high-quality quote from open-source APIs."""
    try:
        # 1. Try ZenQuotes (Very stable)
        resp = requests.get("https://zenquotes.io/api/random", timeout=3)
        if resp.status_code == 200:
            data = resp.json()[0]
            return {"quote": data['q'], "author": data['a']}
    except:
        pass
        
    try:
        # 2. Try Quotable (Good for tags/moods)
        tag_map = {
            'inspiring': 'inspirational',
            'calm': 'happiness',
            'energetic': 'motivational',
            'philosophical': 'wisdom',
            'stoic': 'stoicism',
            'zen': 'zen'
        }
        tag = tag_map.get(mood.lower(), '')
        url = f"https://api.quotable.io/random{f'?tags={tag}' if tag else ''}"
        resp = requests.get(url, timeout=3)
        if resp.status_code == 200:
            data = resp.json()
            return {"quote": data['content'], "author": data['author']}
    except:
        pass
        
    return None


def generate_quote(prompt: str, mood: str = "", max_length: int = 60) -> str:
    """Generates a quote using a fine-tuned prompt with the local model."""
    
    # 1. Attempt to fetch from open-source APIs for variety
    os_quote = fetch_open_source_quote(mood)
    if os_quote and random.random() < 0.5: # 50% chance to use API quote
        return f'"{os_quote["quote"]}" - {os_quote["author"]}'

    # 2. Fallback to local generation with a more creative prompt
    if not HAS_GENERATOR:
        return "The journey of a thousand miles begins with a single step. - Lao Tzu"
        
    # Construct a more artistic and detailed prompt
    base_prompt = f"Create a profound and original quote about '{prompt}' in a {mood or 'thought-provoking'} style:"
    
    try:
        result = generator(
            base_prompt,
            max_new_tokens=max_length,
            num_return_sequences=1,
            do_sample=True,
            temperature=0.9,
            top_p=0.95,
            pad_token_id=generator.tokenizer.eos_token_id
        )
        
        generated_text = result[0]['generated_text'].replace(base_prompt, "").strip()
        
        # Clean the output to be just the quote
        if '"' in generated_text:
            generated_text = generated_text.split('"')[1]
        
        return generated_text or "To find the universal, look within the particular."

    except Exception as e:
        print(f"Quote generation error: {e}")
        return "The seed of an idea is a universe in waiting."
