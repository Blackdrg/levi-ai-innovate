import os
import uuid
import logging
import asyncio
from typing import Optional, Dict, Any
from pydub import AudioSegment
from pydub.silence import split_on_silence
from backend.engines.voice.stt import SovereignSTT
from backend.engines.voice.tts import SovereignTTS

logger = logging.getLogger(__name__)

class VoiceProcessor:
    """
    Sovereign Voice Orchestration Layer.
    Connects STT -> LEVI Orchestrator -> TTS.
    Hardened v15.0 GA: Includes Silence Trimming and Confidence Gating.
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

    async def _trim_silence(self, input_path: str) -> str:
        """Removes leading/trailing silence to optimize transcription latency."""
        output_path = input_path.replace(".webm", "_trimmed.wav")
        try:
            audio = AudioSegment.from_file(input_path)
            # Trim silence: -40dBFS threshold, 500ms min silence
            trimmed = audio.strip_silence(silence_len=500, silence_thresh=-40)
            trimmed.export(output_path, format="wav")
            return output_path
        except Exception as e:
            logger.warning(f"[VoiceProcessor] Silence trimming failed: {e}. Using raw audio.")
            return input_path

    async def process_voice_command(
        self, 
        audio_bytes: bytes, 
        user_id: str, 
        orchestrator_ref: Any,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Full pipeline with v15.0 Safety Gates.
        """
        self._ensure_engines()
        raw_input = os.path.join(self.tmp_dir, f"{uuid.uuid4()}.webm")
        
        with open(raw_input, "wb") as f:
            f.write(audio_bytes)

        processed_input = await self._trim_silence(raw_input)

        try:
            # 2. Transcribe with resilience
            stt_result = await self.stt.transcribe(processed_input)
            user_text = stt_result.get("text")
            avg_logprob = stt_result.get("avg_logprob", 0)
            
            if not user_text or stt_result.get("provider") == "failed":
                return {"status": "error", "message": "Could not understand audio signature."}

            # v15.0 Bayesian Safety Gate: Check transcription quality
            if avg_logprob < -1.2:
                logger.warning(f"[VoiceProcessor] CRITICAL: Low transcription confidence ({avg_logprob}). Requesting manual verification.")
                return {
                    "status": "verify_required",
                    "transcription": user_text,
                    "confidence": avg_logprob,
                    "message": "The cognitive node is unsure of the command. Please verify or re-speak."
                }

            logger.info(f"[VoiceProcessor] Validated Command: {user_text} (Conf: {avg_logprob})")

            # 3. Trigger Mission via Orchestrator with Voice Metadata
            mission_res = await orchestrator_ref.handle_mission(
                user_id=user_id,
                objective=user_text,
                session_id=session_id or f"voice-{uuid.uuid4().hex[:8]}",
                mode="AUTONOMOUS",
                request_id=f"voice-{uuid.uuid4().hex[:12]}",
                metadata={"interaction_medium": "VOICE", "avg_logprob": avg_logprob}
            )
            
            response_text = mission_res.get("response", "Sovereign thought pulse generated.")
            
            # 4. TTS Response
            output_filename = f"resp-{uuid.uuid4().hex[:8]}.wav"
            output_file = os.path.join(self.tmp_dir, output_filename)
            await self.tts.generate_speech_async(response_text, output_file)

            return {
                "status": "success",
                "transcription": user_text,
                "response_text": response_text,
                "audio_url": f"/api/v1/voice/stream/{output_filename}", 
                "mission_id": mission_res.get("request_id"),
                "provider": stt_result.get("provider")
            }

        except Exception as e:
            logger.error(f"[VoiceProcessor] Pipeline failure: {e}")
            return {"status": "error", "message": "Neural voice gateway timeout."}
        finally:
            for f in [raw_input, processed_input]:
                if os.path.exists(f) and f.endswith("_trimmed.wav"):
                    try: os.remove(f)
                    except: pass
