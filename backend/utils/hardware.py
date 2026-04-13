# backend/utils/hardware.py
import logging
import asyncio
import io
import platform
from typing import Dict, Any, Optional

try:
    import pyaudio
    HAS_PYAUDIO = True
except ImportError:
    HAS_PYAUDIO = False

try:
    import sounddevice as sd
    import soundfile as sf
    HAS_SOUND = True
except ImportError:
    HAS_SOUND = False

try:
    import pynvml
    HAS_NVML = True
except ImportError:
    HAS_NVML = False

logger = logging.getLogger(__name__)

class MicrophoneInput:
    """
    Sovereign v15.0: Hardware Microphone Interface.
    Phase 1: Duration-based recording.
    """
    def __init__(self, sample_rate=16000, chunk_size=1024):
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        self.audio = pyaudio.PyAudio() if HAS_PYAUDIO else None

    async def record_audio(self, duration_seconds: int) -> bytes:
        """Record audio from microphone for a fixed duration."""
        if not HAS_PYAUDIO:
            logger.error("[Hardware] PyAudio not installed. Recording unavailable.")
            return b""

        logger.info(f"[Hardware] Recording audio for {duration_seconds}s...")
        
        # Run in thread to avoid blocking event loop
        return await asyncio.to_thread(self._record_sync, duration_seconds)

    def _record_sync(self, duration: int) -> bytes:
        stream = self.audio.open(
            format=pyaudio.paFloat32,
            channels=1,
            rate=self.sample_rate,
            input=True,
            frames_per_buffer=self.chunk_size
        )
        
        frames = []
        for _ in range(int(self.sample_rate / self.chunk_size * duration)):
            data = stream.read(self.chunk_size)
            frames.append(data)
        
        stream.stop_stream()
        stream.close()
        
        return b''.join(frames)

class SpeakerOutput:
    """
    Sovereign v15.0: Hardware Speaker Interface.
    """
    def __init__(self, sample_rate=22050):
        self.sample_rate = sample_rate

    async def play_audio(self, audio_bytes: bytes):
        """Play audio through system speaker."""
        if not HAS_SOUND:
            logger.error("[Hardware] sounddevice/soundfile not installed. Playback unavailable.")
            return

        logger.info("[Hardware] Playing audio to speakers...")
        await asyncio.to_thread(self._play_sync, audio_bytes)

    def _play_sync(self, audio_bytes: bytes):
        try:
            data, sr = sf.read(io.BytesIO(audio_bytes))
            sd.play(data, sr)
            sd.wait()
        except Exception as e:
            logger.error(f"[Hardware] Playback failed: {e}")

class GPUMonitor:
    """
    Sovereign v15.0: High-fidelity GPU Telemetry.
    Uses NVML for precise NVIDIA metrics.
    """
    def __init__(self):
        self.has_gpu = False
        if HAS_NVML:
            try:
                pynvml.nvmlInit()
                self.has_gpu = True
                logger.info("[Hardware] NVML initialized. GPU monitoring active.")
            except Exception as e:
                logger.warning(f"[Hardware] NVML init failed: {e}")

    def get_vram_usage(self) -> Dict[str, Any]:
        """Get VRAM usage metrics in GB."""
        if not self.has_gpu:
            return {"available": 0, "total": 0, "percent": 0, "active": False}
        
        try:
            handle = pynvml.nvmlDeviceGetHandleByIndex(0)
            info = pynvml.nvmlDeviceGetMemoryInfo(handle)
            
            return {
                "available": info.free / (1024**3),
                "total": info.total / (1024**3),
                "used": info.used / (1024**3),
                "percent": (info.used / info.total) * 100,
                "active": True
            }
        except Exception as e:
            logger.error(f"[Hardware] Memory query failed: {e}")
            return {"active": False}

    def is_vram_available(self, required_gb: float) -> bool:
        usage = self.get_vram_usage()
        if not usage.get("active"):
            return False
        return usage["available"] >= required_gb

    @staticmethod
    def get_device():
        """Helper to return torch-compatible device string."""
        import torch
        if torch.cuda.is_available():
            return "cuda"
        elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            return "mps"
        return "cpu"

# Singleton instance for system-wide monitoring
gpu_monitor = GPUMonitor()
