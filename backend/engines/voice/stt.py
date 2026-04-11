import os
import whisper
import torch
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class SovereignSTT:
    """
    Sovereign Speech-to-Text Engine (Whisper).
    Self-hosted, high-fidelity transcription for LEVI-AI.
    """
    def __init__(self, model_size: str = "small", device: Optional[str] = None):
        self.model_size = model_size
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.model = None
        
        logger.info(f"[STT] Initializing Whisper ({self.model_size}) on {self.device}...")
        self.load_model()

    def load_model(self):
        """Loads or downloads the Whisper model locally."""
        try:
            self.model = whisper.load_model(self.model_size, device=self.device)
            logger.info(f"[STT] Model {self.model_size} loaded successfully.")
        except Exception as e:
            logger.error(f"[STT] Failed to load model: {e}")
            raise

    async def transcribe(self, audio_path: str, language: Optional[str] = None) -> dict:
        """
        Transcribes audio from a file.
        :param audio_path: Path to the audio file (WebM, WAV, MP3, etc.)
        :param language: Optional language hint (e.g., 'en', 'hi')
        :return: Dict containing 'text' and 'segments'
        """
        if not self.model:
            raise RuntimeError("STT Model not initialized.")

        logger.info(f"[STT] Transcribing: {audio_path}")
        
        # Whisper transcription is blocking, so we run it in a thread pool if needed,
        # but for simplicity in Phase 1 we use it directly or via asyncio helper.
        import asyncio
        from functools import partial
        
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None, 
            partial(self.model.transcribe, audio_path, language=language)
        )
        
        return {
            "text": result.get("text", "").strip(),
            "segments": result.get("segments", []),
            "language": result.get("language", "unknown")
        }

    def transcribe_sync(self, audio_path: str, language: Optional[str] = None) -> dict:
        """Synchronous transcription."""
        return self.model.transcribe(audio_path, language=language)
