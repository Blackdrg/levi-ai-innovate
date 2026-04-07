import logging
from typing import Dict, Any
from backend.engines.base import EngineBase
from backend.engines.utils.security import SovereignSecurity

logger = logging.getLogger(__name__)

CONTENT_TEMPLATES = {
    "quote": {"max_tokens": 150, "sys": "LEVI-AI Wisdom Master. Topic: {topic}. Tone: {tone}."},
    "essay": {"max_tokens": 1800, "sys": "Sovereign Essayist. Deep exploration of {topic}."},
    "story": {"max_tokens": 1800, "sys": "Sovereign Storyteller. Narrative arc for {topic}."},
    "philosophy": {"max_tokens": 1400, "sys": "Sovereign Philosopher. Structural analysis of {topic}."},
    "code": {"max_tokens": 2000, "sys": "Sovereign Architect. High-fidelity implementation for {topic}."}
}

class StudioContentEngine(EngineBase):
    """
    Sovereign Content Studio.
    Handles long-form creative generation, essays, and structured media scripts.
    Global ready with multi-language synthesis.
    """
    
    def __init__(self):
        super().__init__("StudioContent")

    async def _run(self, content_type: str, topic: str, tone: str = "philosophical", lang: str = "en", **kwargs) -> Dict[str, Any]:
        """
        Executes a creative generation mission.
        """
        self.logger.info(f"Studio Mission: {content_type} on '{topic}' [{tone}]")
        
        template = CONTENT_TEMPLATES.get(content_type, CONTENT_TEMPLATES["essay"])
        max_tokens = template["max_tokens"]
        
        # 1. PII Guard
        safe_topic = SovereignSecurity.mask_pii(topic)
        
        # 2. Build Enriched Prompt
        system_prompt = template["sys"].format(topic=safe_topic, tone=tone)
        if lang != "en":
            system_prompt += f" Output must be entirely in {lang}."
            
        # 3. Engage Council of Models for High-Fidelity Studio Output
        from backend.engines.chat.generation import SovereignGenerator
        generator = SovereignGenerator()
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Create a high-fidelity {content_type} about {safe_topic}."}
        ]
        
        # We use the council for professional studio results
        content = await generator.council_of_models(messages)
        
        return {
            "type": content_type,
            "topic": safe_topic,
            "tone": tone,
            "lang": lang,
            "content": content,
            "word_count": len(content.split())
        }
