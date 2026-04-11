import os
import uuid
import logging
import asyncio
from typing import Optional, Dict, Any
from backend.engines.voice.stt import SovereignSTT
else: # I'll do a proper import check
    pass

# We'll use a lazy initialization pattern for the engines to avoid loading them if not needed
# or to allow specific configurations later.

logger = logging.getLogger(__name__)

class VoiceProcessor:
    """
    Sovereign Voice Orchestration Layer.
    Connects STT -> LEVI Orchestrator -> TTS.
    """
    def __init__(self, stt_engine: Optional[SovereignSTT] = None, tts_engine: Optional[SovereignTTS] = None):
        self.stt = stt_engine
        self.tts = tts_engine
        self.tmp_dir = os.path.join(os.getcwd(), "data", "voice", "tmp")
        os.makedirs(self.tmp_dir, exist_ok=True)

    def _ensure_engines(self):
        """Lazy load engines if not provided."""
        if not self.stt:
            from backend.engines.voice.stt import SovereignSTT
            self.stt = SovereignSTT(model_size="small")
        if not self.tts:
            from backend.engines.voice.tts import SovereignTTS
            self.tts = SovereignTTS()

    async def process_voice_command(
        self, 
        audio_bytes: bytes, 
        user_id: str, 
        orchestrator_ref: Any, # Pass the Orchestrator instance
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Full pipeline: 
        1. Save bytes to tmp file.
        2. Transcribe (STT).
        3. Create Orchestrator Mission.
        4. Generate Speech for Response (TTS).
        5. Return text and audio path.
        """
        self._ensure_engines()
        
        # 1. Save audio to file
        input_file = os.path.join(self.tmp_dir, f"{uuid.uuid4()}.webm")
        with open(input_file, "wb") as f:
            f.write(audio_bytes)

        try:
            # 2. Transcribe
            stt_result = await self.stt.transcribe(input_file)
            user_text = stt_result.get("text")
            
            if not user_text:
                return {"status": "error", "message": "Could not understand audio."}

            logger.info(f"[VoiceGateway] User Command: {user_text}")

            # 3. Trigger Mission via Orchestrator (Graduation #14)
            # Use handle_mission for production state-machine integration
            mission_res = await orchestrator_ref.handle_mission(
                user_id=user_id,
                objective=user_text,
                session_id=session_id or f"voice-{uuid.uuid4().hex[:8]}",
                mode="AUTONOMOUS",
                request_id=f"voice-{uuid.uuid4().hex[:12]}"
            )
            
            response_text = mission_res.get("response", "The thought stream was interrupted.")
            
            # 4. TTS (Speak the response back)
            output_filename = f"resp-{uuid.uuid4().hex[:8]}.wav"
            output_file = os.path.join(self.tmp_dir, output_filename)
            await self.tts.generate_speech_async(response_text, output_file)

            return {
                "status": "success",
                "transcription": user_text,
                "response_text": response_text,
                "audio_url": f"/api/v1/voice/stream/{output_filename}", 
                "mission_id": mission_res.get("request_id")
            }

        except Exception as e:
            logger.error(f"[VoiceGateway] Pipeline error: {e}")
            return {"status": "error", "message": str(e)}
        finally:
            # We keep the files for a short duration or delete them after streaming
            # os.remove(input_file) 
            pass
