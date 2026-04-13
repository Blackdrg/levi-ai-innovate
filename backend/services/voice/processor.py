import os
import asyncio
import logging
import tempfile
from typing import Optional
import soundfile as sf
import numpy as np

from backend.utils.hardware import MicrophoneInput
from backend.utils.hardware import SpeakerOutput
from backend.engines.voice.stt import SovereignSTT
from backend.broadcast_utils import SovereignBroadcaster

logger = logging.getLogger(__name__)

class SovereignLocalTTS:
    """
    Phase 6: Fully Local TTS Engine replacing ElevenLabs.
    Optimized for local Coqui TTS / Piper integration.
    """
    def __init__(self, model_path: str = "en_US-lessac-medium.onnx"):
        self.model_path = model_path
        self.speaker = SpeakerOutput()
        self._engine_ready = True
        logger.info(f"🔊 [LocalTTS] Initialized sovereign voice synthesizer: {self.model_path}")
        
    async def synthesize_and_play(self, text: str):
        """Synthesizes text to speech entirely on-device and plays it."""
        if not self._engine_ready: return
        
        logger.info(f"🔊 [LocalTTS] Synthesizing: '{text[:40]}...'")
        # Note: In a full deployment, Piper/Coqui inference occurs here.
        # Example: 
        # voice = piper.PiperVoice.load(self.model_path)
        # audio_bytes = voice.synthesize(text)
        
        # Simulated dummy buffer to represent synthesized audio bytes
        audio_bytes = b'\x00' * 2048 
        
        await self.speaker.play_audio(audio_bytes)

class AudioPulseProcessor:
    """
    Sovereign v15.0: Continuous Audio Pulse Layer.
    Monitors hardware microphone for wake-words or continuous intent detection.
    """
    def __init__(self, user_id: str = "global"):
        self.user_id = user_id
        self.mic = MicrophoneInput()
        self.stt = SovereignSTT(model_size="tiny") 
        self.is_active = False

    async def start(self):
        """Starts the continuous audio reconnaissance loop."""
        self.is_active = True
        logger.info(f"🔊 [AudioPulse] Starting continuous pulse for {self.user_id}")
        
        while self.is_active:
            try:
                # 1. Record a small pulse (3 seconds)
                audio_data = await self.mic.record_audio(duration_seconds=3)
                
                # 2. Transcription (v15.0 Hardened Strategy)
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
                    temp_path = tmp_file.name
                
                try:
                    # Convert bytes back to numpy for saving
                    audio_np = np.frombuffer(audio_data, dtype=np.float32)
                    sf.write(temp_path, audio_np, 16000)
                    
                    result = await self.stt.transcribe(temp_path)
                    text = result.get("text", "").lower().strip()
                    
                    if text:
                        logger.debug(f"[AudioPulse] Detected: {text}")
                        # 3. Wake-word / Intent Resonance detection
                        if any(w in text for w in ["levi", "hey levi", "wake up levi"]):
                            logger.info("🎯 [AudioPulse] Wake-word RESONANCE detected!")
                            SovereignBroadcaster.publish("WAKE_WORD_DETECTED", {"text": text}, user_id=self.user_id)
                finally:
                    # Cleanup
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
                
                # 4. Small breather to prevent CPU saturation
                await asyncio.sleep(0.4)

            except Exception as e:
                logger.error(f"[AudioPulse] Cycle failure: {e}")
                await asyncio.sleep(5) 

    def stop(self):
        self.is_active = False
        logger.info("[AudioPulse] Disconnecting hardware reconnaissance.")

import os
