import logging
import os
import asyncio
from typing import Any, Dict, List, Optional
from backend.engines.base import EngineBase, EngineResult
from backend.engines.utils.i18n import SovereignI18n
from backend.engines.utils.security import SovereignSecurity

logger = logging.getLogger(__name__)

class ChatEngine(EngineBase):
    """
    Sovereign Chat Interface.
    Handles conversational logic, context window management, and multi-modal focus.
    Global ready with i18n and security guardrails.
    """
    
    def __init__(self):
        super().__init__("Chat")
        self.max_context_tokens = 4096
        self.model_path = os.environ.get("LLAMA_MODEL_PATH", "./models/llama-3-8b.gguf")
        self.llama = None
        self._load_local_model()

    def _load_local_model(self):
        """Attempts to load the local Llama model for sovereign execution."""
        try:
            from llama_cpp import Llama
            if os.path.exists(self.model_path):
                self.llama = Llama(
                    model_path=self.model_path,
                    n_ctx=self.max_context_tokens,
                    verbose=False,
                    n_threads=os.cpu_count() or 4
                )
                self.logger.info(f"Sovereign Llama loaded from {self.model_path}")
            else:
                self.logger.warning(f"Local model not found at {self.model_path}. Fallback enabled.")
        except ImportError:
            self.logger.warning("llama-cpp-python not available. Using API fallback.")
        except Exception as e:
            self.logger.error(f"Inference engine load failure: {e}")

    async def _run(self, query: str, context: Optional[str] = None, mode: str = "chat", lang: str = "en", **kwargs) -> str:
        """
        Main execution logic for the Chat Engine.
        """
        # 1. Apply Security Layer
        safe_query = SovereignSecurity.mask_pii(query)
        safe_context = SovereignSecurity.mask_pii(context) if context else ""
        
        # 2. Build Context-Aware Prompt
        system_prompt = SovereignI18n.get_prompt("system_brain", lang)
        
        if mode == "synthesis":
            full_prompt = SovereignI18n.get_prompt("rag_synthesis", lang, context=safe_context) + f"\nUser Query: {safe_query}"
        else:
            full_prompt = f"{system_prompt}\n\nContext:\n{safe_context}\n\nUser: {safe_query}\nAssistant:"

        # 3. Inference Strategy (Local vs API)
        if self.llama:
            return await self._local_inference(full_prompt, **kwargs)
        else:
            return await self._api_fallback(full_prompt, lang, **kwargs)

    async def _local_inference(self, prompt: str, **kwargs) -> str:
        """Executes inference on the local Llama model."""
        try:
            loop = asyncio.get_event_loop()
            # Run blocking llama call in a thread pool to keep the engine async
            response = await loop.run_in_executor(
                None, 
                lambda: self.llama(
                    prompt,
                    max_tokens=kwargs.get("max_tokens", 512),
                    stop=["User:", "\n\n"],
                    echo=False
                )
            )
            text = response["choices"][0]["text"].strip()
            return f"[Sovereign] {text}"
        except Exception as e:
            self.logger.error(f"Local inference failure: {e}")
            return f"Inference interrupted: {e}"

    async def _api_fallback(self, prompt: str, lang: str, **kwargs) -> str:
        """Simulated API fallback for when local resources are unavailable."""
        self.logger.info("Engaging API Fallback layer...")
        # Placeholder for real OpenAI/Anthropic/Groq integration
        await asyncio.sleep(0.5)
        return f"[Global API] {SovereignI18n.get_prompt('error_fallback', lang)} (Simulation Mode)"

    async def format_response(self, data: Any, format_type: str = "markdown") -> str:
        """Utility to format engine results into high-fidelity UI strings."""
        if format_type == "markdown":
            return f"```json\n{data}\n```"
        return str(data)
