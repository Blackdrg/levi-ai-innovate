import os
import asyncio
import logging
import tempfile
import uuid
from typing import Optional, Any, Dict
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
        """
        Synthesizes text to speech entirely on-device and plays it.
        Uses Piper (Fast, local ONNX-based TTS).
        """
        if not self._engine_ready or not text: return
        
        logger.info(f"🔊 [LocalTTS] Synthesizing: '{text[:40]}...'")
        
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
            output_path = tmp_file.name
        
        try:
            # 1. Piper Inference via Subprocess (Optimized for low overhead)
            # Command: echo "$TEXT" | piper --model $MODEL --output_file $WAV
            import subprocess
            
            # Check for piper in PATH
            piper_cmd = os.getenv("PIPER_PATH", "piper")
            
            process = await asyncio.create_subprocess_exec(
                piper_cmd,
                "--model", self.model_path,
                "--output_file", output_path,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate(input=text.encode())
            
            if process.returncode != 0:
                logger.error(f"[LocalTTS] Piper synthesis failed: {stderr.decode()}")
                return

            # 2. Play the synthesized waveform
            if os.path.exists(output_path):
                # Read WAV bytes
                with open(output_path, "rb") as f:
                    audio_bytes = f.read()
                
                await self.speaker.play_audio(audio_bytes)
                
        except Exception as e:
            logger.error(f"[LocalTTS] Synthesis failure: {e}")
        finally:
            if os.path.exists(output_path):
                os.remove(output_path)

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

class VoiceProcessor:
    """
    Sovereign v15.0 GA: Unified Voice Command Hub.
    Bridges the Voice API with local STT/TTS engines.
    """
    def __init__(self):
        self.stt = SovereignSTT(model_size="small")
        self.tts = SovereignLocalTTS()
        logger.info("🎙️ [VoiceProcessor] Unified Hub Active.")

    async def process_voice_command(self, audio_bytes: bytes, user_id: str, orchestrator_ref: Any) -> Dict[str, Any]:
        """Processes an uploaded audio command, transcribes it, and dispatches a mission."""
        with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as tmp:
            tmp.write(audio_bytes)
            audio_path = tmp.name

        try:
            # 1. Transcribe
            result = await self.stt.transcribe(audio_path)
            text = result.get("text", "").strip()
            
            if not text:
                return {"status": "error", "message": "No speech detected."}

            logger.info(f"🎙️ [VoiceProcessor] Transcribed command: '{text}' (Conf: {result.get('confidence', 0):.2f})")

            # 2. Dispatch Mission if orchestrator is provided
            if orchestrator_ref:
                result = await orchestrator_ref.handle_mission(
                    user_input=text,
                    user_id=user_id,
                    session_id=f"voice-{uuid.uuid4().hex[:8]}"
                )
                return {
                    "status": "success",
                    "transcription": text,
                    "confidence": result.get("confidence", 0.9),
                    "mission_id": result.get("request_id") or "voice-mission"
                }
            
            return {
                "status": "success",
                "transcription": text,
                "confidence": result.get("confidence", 0.9)
            }

        finally:
            if os.path.exists(audio_path):
                os.remove(audio_path)
