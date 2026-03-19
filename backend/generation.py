from transformers import pipeline
import os
import random

import threading

generator = None
HAS_GENERATOR = False
_gen_lock = threading.Lock()

try:
    # generator = pipeline('text-generation', model='gpt2', device=-1)  # CPU
    # HAS_GENERATOR = True
    pass
except Exception as e:
    print(f"Warning: Failed to load text-generation model: {e}")
    HAS_GENERATOR = False

def generate_response(prompt: str, history: list = None, mood: str = "", max_length: int = 100) -> str:
    if not HAS_GENERATOR or generator is None:
        return "I'm currently in 'quote-only' mode. Try asking for a specific topic like 'motivation'!"

    # Build context from history
    context = ""
    if history:
        # Take last 3 exchanges for context
        for msg in history[-3:]:
            context += f"User: {msg.get('user', '')}\nBot: {msg.get('bot', '')}\n"
    
    full_prompt = f"{context}User: {prompt}\nBot:"
    
    try:
        with _gen_lock:
            # Adjust generation parameters for better conversation
            result = generator(
                full_prompt, 
                max_new_tokens=max_length,
                num_return_sequences=1, 
                do_sample=True, 
                temperature=0.7,
                top_p=0.9,
                pad_token_id=50256, # GPT2 end of text token
                truncation=True
            )
        
        generated_text = result[0]['generated_text']
        # Extract only the bot's response
        if "Bot:" in generated_text:
            response = generated_text.split("Bot:")[-1].strip()
        else:
            response = generated_text.replace(full_prompt, "").strip()
            
        # Clean up any trailing User/Bot tags if the model keeps generating
        response = response.split("User:")[0].split("Bot:")[0].strip()
        
        return response or "I'm reflecting on that. What else is on your mind?"
    except Exception as e:
        print(f"Generation error: {e}")
        return "That's an interesting point. Tell me more!"

def generate_quote(prompt: str, mood: str = "", max_length: int = 50) -> str:
    if not HAS_GENERATOR or generator is None:
        return "The best way to predict the future is to create it."
        
    full_prompt = f"Inspirational quote about {mood or 'life'}: {prompt}\nQuote:"
    try:
        with _gen_lock:
            result = generator(full_prompt, max_new_tokens=max_length, num_return_sequences=1, do_sample=True, temperature=0.9)
        generated = result[0]['generated_text']
        if "Quote:" in generated:
            return generated.split("Quote:")[-1].strip().split("\n")[0]
        return generated.replace(full_prompt, "").strip().split("\n")[0]
    except:
        return "Life is what happens when you're busy making other plans."

