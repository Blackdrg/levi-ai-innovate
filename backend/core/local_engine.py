"""
backend/services/orchestrator/local_engine.py

🟢 LOCAL ENGINE v2.0 — Real, Sovereignty-First Local LLM.

Powered by llama-cpp-python (GGUF).
Provides zero-cost, zero-latency (post-load) responses for:
  - Greetings & Identity
  - Simple reasoning tasks (Complexity 1-2)
  - Tool-use planning logic
"""

import os
import logging
import asyncio
from typing import Dict, Any, AsyncGenerator, Optional
try:
    from llama_cpp import Llama  # type: ignore
    HAS_LLAMA_CPP = True
except ImportError:
    Llama = None # type: ignore
    HAS_LLAMA_CPP = False
    import logging
    logger = logging.getLogger(__name__)
    logger.warning("llama-cpp-python not installed. Local LLM degraded mode active.")

logger = logging.getLogger(__name__)
# --- Configuration ---
MODEL_PATH = os.getenv("LOCAL_MODEL_PATH", "backend/data/models/llama-3-8b-instruct.Q4_K_M.gguf")
N_CTX = 4096
N_THREADS = int(os.getenv("LOCAL_LLM_THREADS", "4"))

class LocalLLM:
    """
    Singleton for the local LlamaCPP engine to prevent redundant memory allocation.
    """
    _instance: Optional[Llama] = None
    _lock = asyncio.Lock()
    _concurrency_semaphore = None # Initialized lazily

    @classmethod
    async def get_instance(cls) -> Optional[Llama]:
        if cls._instance is not None:
            return cls._instance

        async with cls._lock:
            if cls._instance is not None:
                return cls._instance

            if not os.path.exists(MODEL_PATH):
                logger.warning(f"Local model not found at {MODEL_PATH}. Local reasoning unavailable.")
                return None

            try:
                # Lazy-loading the model into memory
                logger.info(f"Loading local model: {MODEL_PATH} (Threads: {N_THREADS})")
                cls._instance = Llama(
                    model_path=MODEL_PATH,
                    n_ctx=N_CTX,
                    n_threads=N_THREADS,
                    verbose=False,
                    n_gpu_layers=-1 if os.getenv("USE_GPU", "true").lower() == "true" else 0
                )
                
                # Max 2 concurrent local inferences on 8Gi RAM for stability
                max_concurrency = int(os.getenv("MAX_LOCAL_CONCURRENCY", "2"))
                cls._concurrency_semaphore = asyncio.Semaphore(max_concurrency)
                
                logger.info(f"Local LLM initialized (Concurrency Limit: {max_concurrency})")
                return cls._instance
            except Exception as e:
                logger.error(f"Failed to initialize Local LLM: {e}")
                return None

async def generate_local_response(
    messages: list, 
    max_tokens: int = 512, 
    temperature: float = 0.7
) -> AsyncGenerator[str, None]:
    """
    Streaming generator for local LLM responses.
    """
    llm = await LocalLLM.get_instance()
    if not llm:
        yield "I'm currently unable to process this locally. Please check my status."
        return

    # Check for concurrency saturation
    if LocalLLM._concurrency_semaphore.locked():
        logger.warning("Local engine saturated. Triggering API Fallback...")
        yield "__FALLBACK_TRIGGER__"
        return

    async with LocalLLM._concurrency_semaphore:
        try:
            # Convert messages to prompt format (Llama 3 Instruct template)
            # Note: In a production scenario, we'd use a more robust template engine.
            prompt = ""
            for msg in messages:
                role = msg["role"]
                content = msg["content"]
                if role == "system":
                    prompt += f"<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n\n{content}<|eot_id|>"
                elif role == "user":
                    prompt += f"<|start_header_id|>user<|end_header_id|>\n\n{content}<|eot_id|>"
                elif role == "assistant":
                    prompt += f"<|start_header_id|>assistant<|end_header_id|>\n\n{content}<|eot_id|>"
            
            prompt += "<|start_header_id|>assistant<|end_header_id|>\n\n"

            # Execute streaming generation
            output = llm(
                prompt,
                max_tokens=max_tokens,
                stop=["<|eot_id|>", "<|end_of_text|>"],
                stream=True,
                temperature=temperature
            )

            for chunk in output:
                token = chunk["choices"][0]["text"]
                yield token

        except Exception as e:
            logger.error(f"Local generation error: {e}")
            yield f"Error during local synthesis: {str(e)}"

async def handle_local(user_input: str, context: Dict[str, Any] = {}) -> str:
    """
    Legacy sync/async wrapper for deterministic local handling.
    """
    messages = [
        {"role": "system", "content": "You are LEVI, a helpful AI assistant. Be concise and friendly."},
        {"role": "user", "content": user_input}
    ]
    
    response = ""
    async for token in generate_local_response(messages):
        response += token
    
    return response or "I'm here."

async def handle_local_sync(messages: list, max_tokens: int = 250, temperature: float = 0.1) -> str:
    """
    Perform a single non-streaming local inference. 
    Ideal for internal tasks like intent classification or summarization.
    """
    llm = await LocalLLM.get_instance()
    if not llm: return ""

    try:
        prompt = ""
        for msg in messages:
            prompt += f"<|start_header_id|>{msg['role']}<|end_header_id|>\n\n{msg['content']}<|eot_id|>"
        prompt += "<|start_header_id|>assistant<|end_header_id|>\n\n"

        output = await asyncio.to_thread(
            lambda: llm(
                prompt,
                max_tokens=max_tokens,
                stop=["<|eot_id|>", "<|end_of_text|>"],
                stream=False,
                temperature=temperature
            )
        )
        return output["choices"][0]["text"].strip()
    except Exception as e:
        logger.error(f"Local sync generation failed: {e}")
        return ""

def is_locally_handleable(intent: str, complexity: int) -> bool:
    """
    Predicate used by the Decision Engine to gate routing.
    If the model exists, Level 1 and 2 tasks are redirected here.
    """
    if not HAS_LLAMA_CPP or not os.path.exists(MODEL_PATH):
        return False
        
    return complexity <= 2
