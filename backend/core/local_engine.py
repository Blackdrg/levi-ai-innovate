"""
Sovereign Local Intelligence Core v7.
Powered by llama-cpp-python (GGUF).
Zero-cost, privacy-first inference for high-fidelity local execution.
"""

import os
import logging
import asyncio
from typing import Dict, Any, AsyncGenerator, Optional, List
from backend.engines.utils.security import SovereignSecurity

try:
    from llama_cpp import Llama 
    HAS_LLAMA_CPP = True
except ImportError:
    Llama = None 
    HAS_LLAMA_CPP = False

logger = logging.getLogger(__name__)

# --- Configuration ---
DEFAULT_MODEL = os.getenv("LOCAL_MODEL_PATH", "backend/data/models/llama-3-8b-instruct.Q4_K_M.gguf")
SMALL_MODEL = os.getenv("SMALL_MODEL_PATH", "backend/data/models/phi-3-mini.Q4_K_M.gguf")
N_CTX = 4096
N_THREADS = int(os.getenv("LOCAL_LLM_THREADS", os.cpu_count() or 4))

class LocalLLM:
    """
    Sovereign Singleton for Local LLM Management.
    Supports dynamic loading of 'Small' vs 'Large' models based on task requirement.
    """
    _instances: Dict[str, Llama] = {}
    _lock = asyncio.Lock()
    _semaphore: Optional[asyncio.Semaphore] = None

    @classmethod
    async def get_instance(cls, model_type: str = "default") -> Optional[Llama]:
        """Retrieves or initializes a specific local model instance."""
        model_path = DEFAULT_MODEL if model_type == "default" else SMALL_MODEL
        
        if model_path in cls._instances:
            return cls._instances[model_path]

        async with cls._lock:
            if model_path in cls._instances:
                return cls._instances[model_path]

            if not os.path.exists(model_path):
                logger.warning(f"Local model not found: {model_path}")
                return None

            try:
                logger.info(f"Loading local model [{model_type}]: {model_path}")
                cls._instances[model_path] = Llama(
                    model_path=model_path,
                    n_ctx=N_CTX,
                    n_threads=N_THREADS,
                    verbose=False,
                    n_gpu_layers=-1 # Auto-detect GPU
                )
                
                if cls._semaphore is None:
                    max_concurrency = int(os.getenv("MAX_LOCAL_CONCURRENCY", "2"))
                    cls._semaphore = asyncio.Semaphore(max_concurrency)
                
                return cls._instances[model_path]
            except Exception as e:
                logger.error(f"Local LLM initialization failed: {e}")
                return None

async def generate_local_stream(
    messages: List[Dict], 
    model_type: str = "default",
    max_tokens: int = 512, 
    temperature: float = 0.7
) -> AsyncGenerator[str, None]:
    """
    Hardened streaming generator for local LLM responses.
    Includes memory-aware concurrency gating.
    """
    llm = await LocalLLM.get_instance(model_type)
    if not llm:
        yield "Local intelligence offline. Verify GGUF paths."
        return

    # Concurrency Guard
    if LocalLLM._semaphore.locked():
        logger.warning("Local engine saturated. Yielding fallback trigger.")
        yield "__FALLBACK_TRIGGER__"
        return

    async with LocalLLM._semaphore:
        try:
            # Construct Llama-3 style prompt (Hardened)
            prompt = ""
            for msg in messages:
                role = msg["role"]
                # PII Masking on input
                content = SovereignSecurity.mask_pii(msg["content"])
                prompt += f"<|start_header_id|>{role}<|end_header_id|>\n\n{content}<|eot_id|>"
            prompt += "<|start_header_id|>assistant<|end_header_id|>\n\n"

            # Run blocking inference in a thread room
            output = llm(
                prompt,
                max_tokens=max_tokens,
                stop=["<|eot_id|>", "<|end_of_text|>"],
                stream=True,
                temperature=temperature
            )

            for chunk in output:
                token = chunk["choices"][0]["text"]
                # Mask PII in real-time streaming output
                yield SovereignSecurity.mask_pii(token)

        except Exception as e:
            logger.error(f"Local streaming error: {e}")
            yield f"System interruption: {str(e)}"

async def handle_local_task(query: str, complexity: int = 1) -> str:
    """Non-streaming entry point for structural tasks (intent/routing)."""
    model_type = "small" if complexity <= 1 else "default"
    
    messages = [
        {"role": "system", "content": "You are LEVI-AI Sovereign Local. Be precise."},
        {"role": "user", "content": query}
    ]
    
    response = ""
    async for token in generate_local_stream(messages, model_type=model_type):
        if token == "__FALLBACK_TRIGGER__": return "FALLBACK"
        response += token
    
    return response.strip()
