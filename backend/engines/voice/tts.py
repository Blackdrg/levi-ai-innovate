import os
import logging
from typing import Optional, List
from TTS.api import TTS
import torch

logger = logging.getLogger(__name__)

class SovereignTTS:
    """
    Sovereign Text-to-Speech Engine (Coqui).
    Local high-quality voice generation.
    """
    def __init__(self, model_name: str = "tts_models/en/ljspeech/vits", device: Optional[str] = None):
        self.model_name = model_name
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.tts = None

        logger.info(f"[TTS] Initializing Coqui TTS ({self.model_name}) on {self.device}...")
        self.load_model()

    def load_model(self):
        """Loads the TTS model locally."""
        try:
            # We use the standard VITS model for high speed and local privacy
            self.tts = TTS(model_name=self.model_name, progress_bar=False).to(self.device)
            logger.info(f"[TTS] Model {self.model_name} loaded successfully.")
        except Exception as e:
            logger.error(f"[TTS] Failed to load TTS model: {e}")
            raise

    def generate_speech(self, text: str, output_path: str, speaker_wav: Optional[str] = None, language: str = "en"):
        """
        Generates speech from text and saves to a file.
        :param text: Text to speak
        :param output_path: Destination path for the .wav file
        :param speaker_wav: Optional wav file for voice cloning (if using multi-speaker model)
        :param language: Language code
        """
        if not self.tts:
            raise RuntimeError("TTS Engine not initialized.")

        logger.info(f"[TTS] Generating speech for: {text[:50]}...")
        
        # Check if model supports multiple speakers
        if self.tts.is_multi_speaker and speaker_wav:
             self.tts.tts_to_file(text=text, speaker_wav=speaker_wav, language=language, file_path=output_path)
        else:
             self.tts.tts_to_file(text=text, file_path=output_path)
             
        return output_path

    async def generate_speech_async(self, text: str, output_path: str, **kwargs):
        """Async wrapper for speech generation."""
        import asyncio
        from functools import partial
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, partial(self.generate_speech, text, output_path, **kwargs))

    def list_models(self) -> List[str]:
        """Lists available local models."""
        return TTS().list_models()
