
import asyncio
import logging
from typing import Optional
from backend.utils.hardware import MicrophoneInput
from backend.engines.voice.stt import SovereignSTT
from backend.broadcast_utils import SovereignBroadcaster

logger = logging.getLogger(__name__)

class AudioPulseProcessor:
    """
    Sovereign v15.0: Continuous Audio Pulse Layer.
    Monitors hardware microphone for wake-words or continuous intent detection.
    """
    def __init__(self, user_id: str = "global"):
        self.user_id = user_id
        self.mic = MicrophoneInput()
        self.stt = SovereignSTT(model_size="tiny") # Use tiny for low-latency continuous monitor
        self.is_active = False

    async def start(self):
        """Starts the continuous audio reconnaissance loop."""
        self.is_active = True
        logger.info(f"🔊 [AudioPulse] Starting continuous pulse for {self.user_id}")
        
        while self.is_active:
            try:
                # 1. Record a small pulse (3 seconds)
                audio_data = await self.mic.record_audio(duration_seconds=3)
                
                # 2. Transcription (v15.0 Hardened)
                # In a real scenario, we'd save to a temp file or stream directly
                temp_path = f"tmp/pulse_{self.user_id}.wav"
                os.makedirs("tmp", exist_ok=True)
                
                import soundfile as sf
                import numpy as np
                # Convert bytes back to numpy for saving
                audio_np = np.frombuffer(audio_data, dtype=np.float32)
                sf.write(temp_path, audio_np, 16000)
                
                result = await self.stt.transcribe(temp_path)
                text = result.get("text", "").lower()
                
                if text:
                    logger.debug(f"[AudioPulse] Detected: {text}")
                    # 3. Wake-word / Intent Resonance detection
                    if "levi" in text or "hey levi" in text:
                        logger.info("🎯 [AudioPulse] Wake-word RESONA NCE detected!")
                        SovereignBroadcaster.publish("WAKE_WORD_DETECTED", {"text": text}, user_id=self.user_id)
                
                # 4. Small breather to prevent CPU saturation
                await asyncio.sleep(0.5)

            except Exception as e:
                logger.error(f"[AudioPulse] Cycle failure: {e}")
                await asyncio.sleep(5) # Backoff on failure

    def stop(self):
        self.is_active = False
        logger.info("[AudioPulse] Disconnecting hardware reconnaissance.")

import os
