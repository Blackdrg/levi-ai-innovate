import asyncio
import os
import logging
import sys

# Add the project root to sys.path for local imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.utils.llm_utils import call_ollama_llm, call_lightweight_llm

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_ollama_connectivity():
    """
    Verifies that LEVI-AI can communicate with the local Ollama daemon.
    """
    print("\n--- Phase 1: Ollama Connectivity Check ---")
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    model = os.getenv("OLLAMA_MODEL", "llama3")
    
    print(f"Target URL: {base_url}")
    print(f"Target Model: {model}")
    
    test_messages = [{"role": "user", "content": "Say 'Neural signal received' if you are active."}]
    
    result = await call_ollama_llm(test_messages, model=model)
    
    if "Neural signal received" in result or result:
        print(f"✅ Success! Response: {result.strip()}")
    else:
        print("❌ Failure: Could not reach Ollama or model not pulled.")
        print("Tip: Run 'ollama pull llama3' in your terminal.")

async def test_hybrid_fallback():
    """
    Verifies the hybrid fallback logic in llm_utils.
    """
    print("\n--- Phase 2: Hybrid Fallback Logic Check ---")
    
    test_messages = [{"role": "user", "content": "What is 2+2?"}]
    
    # This should use Ollama if OLLAMA_BASE_URL is set
    result = await call_lightweight_llm(test_messages)
    
    print(f"Result: {result.strip()}")
    print("Check backend logs to verify if [Ollama] or [LLM-Utils] (Groq) was used.")

if __name__ == "__main__":
    if not os.getenv("OLLAMA_BASE_URL"):
        print("⚠️ Warning: OLLAMA_BASE_URL is not set in environment.")
        print("Setting temporary environment variables for testing...")
        os.environ["OLLAMA_BASE_URL"] = "http://localhost:11434"
        os.environ["OLLAMA_MODEL"] = "llama3"

    asyncio.run(test_ollama_connectivity())
    asyncio.run(test_hybrid_fallback())
