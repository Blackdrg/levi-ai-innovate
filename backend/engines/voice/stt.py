import os
import torch
import logging
import time
from typing import Optional, List, Dict, Any
from faster_whisper import WhisperModel
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)

class SovereignSTT:
    """
    Sovereign Speech-to-Text Engine (Faster-Whisper).
    Optimized via CTranslate2 for ultra-low latency transcription.
    Includes Cloud-Fallback for mission-critical resilience.
    """
    def __init__(self, model_size: str = "small", device: Optional[str] = None, compute_type: str = "float16"):
        self.model_size = model_size
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        
        if self.device == "cpu":
            compute_type = "int8"
        self.compute_type = compute_type

        logger.info(f"[STT] Initializing Faster-Whisper ({self.model_size}) on {self.device} ({self.compute_type})...")
        try:
            self.model = WhisperModel(self.model_size, device=self.device, compute_type=self.compute_type)
        except Exception as e:
            logger.error(f"[STT] Local model load failed: {e}. System will rely on Cloud-Fallback.")
            self.model = None

        api_key = os.getenv("OPENAI_API_KEY")
        self.openai_client = AsyncOpenAI(api_key=api_key) if api_key else None

    async def transcribe(self, audio_path: str, language: Optional[str] = None) -> Dict[str, Any]:
        """
        Transcribes audio with automatic fallback to Cloud STT if local fails.
        """
        if not self.model:
            return await self._cloud_fallback(audio_path, reason="Local model uninitialized")

        try:
            logger.info(f"[STT] Initiating Local Transcription: {audio_path}")
            
            import asyncio
            from functools import partial
            loop = asyncio.get_event_loop()
            
            # Non-blocking executor for generator consumption
            segments_gen, info = await loop.run_in_executor(
                None, 
                partial(self.model.transcribe, audio_path, language=language, beam_size=5, word_timestamps=True)
            )
            
            segments = list(segments_gen)
            full_text = "".join([s.text for s in segments]).strip()
            
            # v15.0 Safety Metric: Calculate average probability across segments
            avg_prob = sum([s.avg_logprob for s in segments]) / len(segments) if segments else 0
            
            # Confidence check: If average logprob is too low, we might want to fallback anyway
            if avg_prob < -1.0 and os.getenv("OPENAI_API_KEY"):
                logger.warning(f"[STT] Low local confidence ({avg_prob}), triggering Cloud Fallback.")
                return await self._cloud_fallback(audio_path, reason="Low local confidence")

            return {
                "text": full_text,
                "segments": [{"start": s.start, "end": s.end, "text": s.text, "prob": s.avg_logprob} for s in segments],
                "language": info.language,
                "confidence": info.language_probability,
                "avg_logprob": avg_prob,
                "provider": "local"
            }

        except Exception as e:
            logger.error(f"[STT] Local transcription failed: {e}")
            return await self._cloud_fallback(audio_path, reason=str(e))

    async def _cloud_fallback(self, audio_path: str, reason: str = "Unknown") -> Dict[str, Any]:
        """Fallbacks to OpenAI Whisper API for mission continuity."""
        if not os.getenv("OPENAI_API_KEY"):
            logger.error(f"[STT] Cloud Fallback requested ({reason}) but OPENAI_API_KEY is missing.")
            return {"text": "", "error": f"STT Failure: {reason}", "provider": "failed"}

        logger.info(f"[STT] CLOUD FALLBACK INITIATED: {reason}")
        try:
            with open(audio_path, "rb") as audio_file:
                transcript = await self.openai_client.audio.transcriptions.create(
                    model="whisper-1", 
                    file=audio_file,
                    response_format="verbose_json"
                )
            
            return {
                "text": transcript.text,
                "language": getattr(transcript, "language", "en"),
                "confidence": 1.0, # Cloud assumed high confidence for now
                "provider": "openai_cloud"
            }
        except Exception as e:
            logger.error(f"[STT] Cloud Fallback also failed: {e}")
            return {"text": "", "error": f"Critical STT Failure: {e}", "provider": "failed"}
