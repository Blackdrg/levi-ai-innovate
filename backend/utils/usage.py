import logging
import tiktoken
from typing import Optional

logger = logging.getLogger(__name__)

# Cache for tokenizers
TOKENIZERS = {}

def get_tokenizer(model_name: str = "gpt-4"):
    """
    Retrieves or initializes a tiktoken encoder for the specified model.
    Defaults to GPT-4 encoding if model is unknown.
    """
    if model_name in TOKENIZERS:
        return TOKENIZERS[model_name]
    
    try:
        # Map some common LEVI designations to OpenAI models
        model_map = {
            "vision": "gpt-4-vision-preview",
            "artisan": "gpt-4",
            "scout": "gpt-3.5-turbo",
            "research": "gpt-4",
            "local": "gpt-3.5-turbo" # Use 3.5 proxy for local BPE
        }
        
        target = model_map.get(model_name.lower(), "gpt-4")
        enc = tiktoken.encoding_for_model(target)
        TOKENIZERS[model_name] = enc
        return enc
    except Exception as e:
        logger.warning(f"[Usage] Failed to load tokenizer for {model_name}, using cl100k_base: {e}")
        enc = tiktoken.get_encoding("cl100k_base")
        TOKENIZERS[model_name] = enc
        return enc

def count_tokens(text: str, model_name: str = "gpt-4", external_tokens: Optional[int] = None) -> int:
    """
    Counts tokens. Prioritizes externally provided metrics (from cloud providers) 
    then falls back to local tiktoken estimation.
    """
    if external_tokens is not None:
        return external_tokens
        
    if not text:
        return 0
    
    try:
        tokenizer = get_tokenizer(model_name)
        return len(tokenizer.encode(text))
    except Exception as e:
        logger.error(f"[Usage] Token count fallback: {e}")
        return len(text) // 4

def estimate_cost(tokens: int, model_name: str = "gpt-4") -> float:
    """
    Estimates cost in USD based on token count and model.
    Rates are averages for v13 Sovereign OS (2026).
    """
    # Rates per 1k tokens (Input + Output average)
    rates = {
        "gpt-4": 0.03,
        "gpt-4-turbo": 0.01,
        "gpt-3.5-turbo": 0.001,
        "local": 0.0, # Sovereign benefit
        "vision": 0.01
    }
    
    rate = rates.get(model_name.lower(), 0.01)
    return (tokens / 1000.0) * rate
