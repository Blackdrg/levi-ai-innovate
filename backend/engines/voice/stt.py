import os
import torch
import logging
from typing import Optional, List, Dict, Any
from faster_whisper import WhisperModel

logger = logging.getLogger(__name__)

class SovereignSTT:
    """
    Sovereign Speech-to-Text Engine (Faster-Whisper).
    Optimized via CTranslate2 for ultra-low latency transcription.
    """
    def __init__(self, model_size: str = "small", device: Optional[str] = None, compute_type: str = "float16"):
        self.model_size = model_size
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        
        # Determine optimal compute type
        if self.device == "cpu":
            compute_type = "int8"
        self.compute_type = compute_type

        logger.info(f"[STT] Initializing Faster-Whisper ({self.model_size}) on {self.device} ({self.compute_type})...")
        self.model = WhisperModel(self.model_size, device=self.device, compute_type=self.compute_type)

    async def transcribe(self, audio_path: str, language: Optional[str] = None) -> dict:
        """
        Transcribes audio from a file using Faster-Whisper's optimized generator.
        :param audio_path: Path to the audio file.
        :param language: Optional language hint.
        :return: Dict containing 'text' and 'segments'
        """
        if not self.model:
            raise RuntimeError("STT Model not initialized.")

        logger.info(f"[STT] Transcribing (Fast): {audio_path}")
        
        import asyncio
        from functools import partial
        
        loop = asyncio.get_event_loop()
        # running generator consumption in executor to keep event loop free
        segments_gen, info = await loop.run_in_executor(
            None, 
            partial(self.model.transcribe, audio_path, language=language, beam_size=5)
        )
        
        segments = list(segments_gen) # Consumption triggers the heavy lifting
        full_text = "".join([s.text for s in segments]).strip()
        
        return {
            "text": full_text,
            "segments": [{"start": s.start, "end": s.end, "text": s.text} for s in segments],
            "language": info.language,
            "language_probability": info.language_probability
        }

    def transcribe_sync(self, audio_path: str, language: Optional[str] = None) -> dict:
        """Synchronous transcription."""
        segments_gen, info = self.model.transcribe(audio_path, language=language, beam_size=5)
        segments = list(segments_gen)
        return {
            "text": "".join([s.text for s in segments]).strip(),
            "segments": [{"start": s.start, "end": s.end, "text": s.text} for s in segments],
            "language": info.language
        }
