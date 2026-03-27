# pyright: reportMissingImports=false
"""
Router Agent for LEVI AI.
Classifies user intent to route messages to proper service (Chat, Image, Video, Content).
"""
import os
import json
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class RouterAgent:
    def __init__(self):
        self.api_key = os.getenv("GROQ_API_KEY")
        self.client = None
        if self.api_key:
            from backend.firestore_db import db as firestore_db  # type: ignore
            from backend.embeddings import embed_text  # type: ignore
            try:
                import groq  # type: ignore
                self.client = groq.Groq(api_key=self.api_key)
            except ImportError:
                logger.warning("[RouterAgent] Groq SDK not installed.")

    def classify_intent(self, message: str) -> Dict[str, Any]:
        """
        Classify intent of user message.
        Returns dict with 'intent' and 'parameters'.
        """
        client = self.client
        if not client:
            return self._fallback_classify(message)

        prompt = f"""
        You are LEVI Router Agent. Your absolute job is to classify the INTENT of the user message.
        Available Intents:
        1. 'generate_image': User wants an image, photo, painting, drawing, or visual created.
        2. 'generate_video': User wants a video, animation, or reel made.
        3. 'generate_content': User wants long-form content (essay, script, story, blog, thread, poem, caption).
        4. 'chat': General conversation, philosophy discussion, greetings, questions.

        Guidelines:
        - If they mention "draw", "make image", "paint", it's 'generate_image'.
        - If they mention "make video", "create clip", it's 'generate_video'.
        - If they mention "write an essay", "write a script", "write a story", it's 'generate_content'.
           -> For content, identify the 'type' (essay, story, script, etc.).

        Output ONLY structured JSON:
        {{
            "intent": "generate_image" | "generate_video" | "generate_content" | "chat",
            "confidence": 0.0 to 1.0,
            "parameters": {{
                "topic": "extracted topic",
                "mood": "inferred mood (optional)",
                "style": "inferred style for image/video (optional)",
                "content_type": "essay/story/etc (only for generate_content)"
            }}
        }}

        Message: "{message}"
        """

        try:
            response = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=200,
                temperature=0.3, # low temperature for deterministic classification
            )
            raw = response.choices[0].message.content.strip()
            
            # Robust JSON extraction: look for first '{' and last '}'
            try:
                start = raw.find('{')
                end = raw.rfind('}') + 1
                if start != -1 and end != 0:
                    json_str = raw[start:end]
                    data = json.loads(json_str)
                else:
                    raise ValueError("No JSON block found in LLM response")
            except (json.JSONDecodeError, ValueError) as je:
                logger.warning(f"[RouterAgent] JSON parse error: {je}. Raw output snip: {raw[:50]}...")
                return self._fallback_classify(message)

            # Safe truncation for logging
            msg_snip = message[:30] + "..." if len(message) > 30 else message
            logger.info(f"[RouterAgent] '{msg_snip}' -> {data.get('intent')}")
            return data
        except Exception as e:
            logger.error(f"[RouterAgent] LLM classification error: {e}")
            return self._fallback_classify(message)

    def _fallback_classify(self, message: str) -> Dict[str, Any]:
        """Keyword-based fallback classifier."""
        msg = message.lower().strip()
        
        visual = ["image", "picture", "draw", "paint", "canvas", "photo", "background", "wallpaper"]
        video = ["video", "clip", "reel", "avatar", "movie"]
        content_triggers = ["essay", "story", "script", "blog", "thread", "poem", "caption"]

        if any(w in msg for w in video):
            return {"intent": "generate_video", "confidence": 0.6, "parameters": {"topic": message}}
        if any(w in msg for w in visual):
            return {"intent": "generate_image", "confidence": 0.6, "parameters": {"topic": message}}
        
        for t in content_triggers:
            if t in msg:
                return {"intent": "generate_content", "confidence": 0.6, "parameters": {"topic": message, "content_type": t}}

        return {"intent": "chat", "confidence": 0.8, "parameters": {"topic": message}}
