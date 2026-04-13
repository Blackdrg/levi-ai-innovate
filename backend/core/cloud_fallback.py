import os
import logging
import httpx
from typing import List, Dict, Optional
from backend.config.system import CLOUD_FALLBACK_ENABLED
from backend.utils.network import together_breaker, groq_breaker

logger = logging.getLogger(__name__)

class CloudFallbackProxy:
    """
    Sovereign Cloud Fallback Proxy v13.1.
    Routes high-fidelity missions to Anthropic/OpenAI when local 70B slots are saturated.
    """
    
    def __init__(self):
        self.anthropic_key = os.getenv("ANTHROPIC_API_KEY")
        self.openai_key = os.getenv("OPENAI_KEY")
        self.together_key = os.getenv("TOGETHER_API_KEY")
        self.enabled = CLOUD_FALLBACK_ENABLED

    async def generate_together(self, messages: List[Dict], model: str = "meta-llama/Llama-3.1-405b-instruct-turbo") -> Optional[str]:
        """Routes to Together AI via the hardened circuit breaker."""
        if not self.enabled or not self.together_key:
            return None
        
        async def _call():
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    "https://api.together.xyz/v1/chat/completions",
                    headers={"Authorization": f"Bearer {self.together_key}"},
                    json={
                        "model": model,
                        "messages": messages,
                        "max_tokens": 1024,
                        "temperature": 0.7
                    }
                )
                resp.raise_for_status()
                return resp.json()["choices"][0]["message"]["content"]

        try:
            return await together_breaker.async_call(_call)
        except Exception as e:
            logger.error(f"[CloudFallback] TogetherAI failure: {e}")
            return None

    async def select_best_fallback(self, messages: List[Dict], complexity: float = 1.0) -> Optional[str]:
        """
        Heuristic-based fallback selection:
        - Complexity < 0.7: TogetherAI (Llama 3.1 70B/405B) - Efficiency/Parity
        - Complexity >= 0.7: Anthropic (Claude 3.5 Sonnet) - High-Fidelity Reasoning
        """
        if complexity < 0.7:
            res = await self.generate_together(messages)
            if res: return res
        
        # Escalation path
        res = await self.generate_overflow(messages)
        return res

    @classmethod
    async def should_fallback(cls, r_client, wait_time: float) -> bool:
        """
        Checks if we should trigger cloud fallback base on wait time (>90s).
        """
        if wait_time > 90 and CLOUD_FALLBACK_ENABLED:
            # Check if tenant has cloud permission (optional refinement)
            return True
        return False
