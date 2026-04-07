import os
import time
import logging
import httpx
from typing import List, Dict, Optional
from backend.config.system import CLOUD_FALLBACK_ENABLED

logger = logging.getLogger(__name__)

class CloudFallbackProxy:
    """
    Sovereign Cloud Fallback Proxy v13.1.
    Routes high-fidelity missions to Anthropic/OpenAI when local 70B slots are saturated.
    """
    
    def __init__(self):
        self.anthropic_key = os.getenv("ANTHROPIC_API_KEY")
        self.openai_key = os.getenv("OPENAI_KEY")
        self.enabled = CLOUD_FALLBACK_ENABLED

    async def generate_overflow(self, messages: List[Dict], model: str = "claude-3-5-sonnet-20240620") -> Optional[str]:
        """
        Routes to Cloud API if local resources are saturated.
        """
        if not self.enabled:
            logger.warning("[CloudFallback] Attempted overflow but CLOUD_FALLBACK_ENABLED is false.")
            return None

        if not self.anthropic_key and not self.openai_key:
            logger.error("[CloudFallback] No cloud API keys found. Overflow aborted.")
            return None

        # Logic for Anthropic
        if self.anthropic_key:
            try:
                async with httpx.AsyncClient(timeout=60.0) as client:
                    response = await client.post(
                        "https://api.anthropic.com/v1/messages",
                        headers={
                            "x-api-key": self.anthropic_key,
                            "anthropic-version": "2023-06-01",
                            "content-type": "application/json"
                        },
                        json={
                            "model": model,
                            "max_tokens": 1024,
                            "messages": [m for m in messages if m["role"] != "system"],
                            "system": next((m["content"] for m in messages if m["role"] == "system"), "")
                        }
                    )
                    response.raise_for_status()
                    data = response.json()
                    return data["content"][0]["text"]
            except Exception as e:
                logger.error(f"[CloudFallback] Anthropic API failure: {e}")

        # Logic for OpenAI (fallback from Anthropic)
        if self.openai_key:
            try:
                async with httpx.AsyncClient(timeout=60.0) as client:
                    response = await client.post(
                        "https://api.openai.com/v1/chat/completions",
                        headers={
                            "Authorization": f"Bearer {self.openai_key}",
                            "Content-Type": "application/json"
                        },
                        json={
                            "model": "gpt-4-turbo",
                            "messages": messages,
                            "max_tokens": 1024
                        }
                    )
                    response.raise_for_status()
                    data = response.json()
                    return data["choices"][0]["message"]["content"]
            except Exception as e:
                logger.error(f"[CloudFallback] OpenAI API failure: {e}")

        return None

    @classmethod
    async def should_fallback(cls, r_client, wait_time: float) -> bool:
        """
        Checks if we should trigger cloud fallback base on wait time (>90s).
        """
        if wait_time > 90 and CLOUD_FALLBACK_ENABLED:
            # Check if tenant has cloud permission (optional refinement)
            return True
        return False
