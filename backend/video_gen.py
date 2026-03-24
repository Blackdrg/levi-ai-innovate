# pyright: reportMissingImports=false
"""
Video Composer Pipeline for LEVI AI - Fixed v3.0
Pipeline: Text → Script (Groq) → Image (SD/Together) → Voice (TTS) → Video (MoviePy)
"""
import os
import uuid
import logging
import tempfile
from io import BytesIO
from typing import Optional, Any

logger = logging.getLogger(__name__)

# ── Dependency flags ──────────────────────────────────────────────────────────
HAS_MOVIEPY = False
HAS_TTS = False
HAS_PIL = False

try:
    from PIL import Image, ImageDraw, ImageFont  # type: ignore
    HAS_PIL = True
except ImportError:
    pass

try:
    try:
        from moviepy import ImageClip, TextClip, CompositeVideoClip, AudioFileClip  # type: ignore
    except ImportError:
        from moviepy.editor import ImageClip, TextClip, CompositeVideoClip, AudioFileClip  # type: ignore
    HAS_MOVIEPY = True
except ImportError:
    logger.warning("[VideoGen] MoviePy not installed. Video generation unavailable.")

try:
    from TTS.api import TTS as CoquiTTS  # type: ignore
    HAS_TTS = True
except ImportError:
    pass


# ─────────────────────────────────────────────
# Script Generator
# ─────────────────────────────────────────────
def generate_narration_script(quote: str, author: str, mood: str) -> str:
    """Use Groq to create a brief narration script."""
    try:
        import groq  # type: ignore
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            return f"{quote} — by {author}"
        client = groq.Groq(api_key=api_key)
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{
                "role": "system",
                "content": "You are a narration scriptwriter. Create a brief (max 40 words) evocative narration that reads a quote aloud. Output ONLY the narration text."
            }, {
                "role": "user",
                "content": f'Quote: "{quote}" — {author}\nMood: {mood}'
            }],
            max_tokens=80,
            temperature=0.7,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.warning(f"[Script] Failed: {e}")
        return f'"{quote}" — {author}'


# ─────────────────────────────────────────────
# TTS Engine
# ─────────────────────────────────────────────
_tts_engine: Any = None

def _get_tts():
    global _tts_engine
    if _tts_engine is not None:
        return _tts_engine
    if not HAS_TTS:
        return None
    try:
        _tts_engine = CoquiTTS(model_name="tts_models/en/ljspeech/tacotron2-DDC", progress_bar=False)
        return _tts_engine
    except Exception as e:
        logger.error(f"[TTS] Load failed: {e}")
        return None

def synthesize_speech(text: str) -> Optional[str]:
    """Convert text to WAV. Returns path or None."""
    tts = _get_tts()
    if not tts:
        return None
    try:
        fd, path = tempfile.mkstemp(suffix=".wav", prefix="levi_tts_")
        os.close(fd)
        tts.tts_to_file(text=text, file_path=path)
        return path
    except Exception as e:
        logger.error(f"[TTS] Synthesis failed: {e}")
        return None


# ─────────────────────────────────────────────
# Ken Burns effect
# ─────────────────────────────────────────────
def _apply_ken_burns(clip: Any, duration: float, zoom: float = 0.04) -> Any:
    try:
        import numpy as np  # type: ignore
        from PIL import Image as PILImage  # type: ignore
        w, h = clip.size

        def effect(get_frame, t):
            progress = t / duration
            scale = 1 + zoom * progress
            frame = get_frame(t)
            img = PILImage.fromarray(frame)
            nw, nh = int(w * scale), int(h * scale)
            img = img.resize((nw, nh), PILImage.Resampling.LANCZOS)
            left = (nw - w) // 2
            top = (nh - h) // 2
            img = img.crop((left, top, left + w, top + h))
            return np.array(img)

        return clip.transform(effect)
    except Exception as e:
        logger.warning(f"[KenBurns] Failed: {e}")
        return clip


# ─────────────────────────────────────────────
# Main entry point
# ─────────────────────────────────────────────
def generate_quote_video(
    quote: str,
    author: str = "",
    mood: str = "neutral",
    user_tier: str = "free",
    bg_music: Optional[str] = None,
    with_narration: bool = True,
    with_subtitles: bool = True,
) -> BytesIO:
    """
    Full video pipeline. Returns MP4 bytes.
    Raises ImportError if MoviePy not available.
    """
    if not HAS_MOVIEPY:
        raise ImportError(
            "MoviePy is required for video generation. "
            "Install with: pip install moviepy"
        )
    if not HAS_PIL:
        raise ImportError("Pillow (PIL) is required. Install with: pip install Pillow")

    import numpy as np  # type: ignore

    tmp_files = []

    try:
        # ── Step 1: Background image ──────────────────────────────────────
        try:
            from backend.image_gen import generate_quote_image  # type: ignore
        except ImportError:
            from image_gen import generate_quote_image  # type: ignore

        img_pil = generate_quote_image(
            quote, author, mood,
            size=(1080, 1920),
            user_tier=user_tier,
            return_pil=True,
        )
        img_array = np.array(img_pil)

        duration = 10  # seconds
        clip = ImageClip(img_array).with_duration(duration)  # type: ignore
        clip = _apply_ken_burns(clip, duration)

        # ── Step 2: Narration script ──────────────────────────────────────
        narration_text = quote
        if with_narration:
            narration_text = generate_narration_script(quote, author, mood)

        # ── Step 3: TTS audio ─────────────────────────────────────────────
        audio_path = None
        if with_narration:
            audio_path = synthesize_speech(narration_text)
            if audio_path:
                tmp_files.append(audio_path)

        # ── Step 4: Compose ───────────────────────────────────────────────
        final_clip = clip

        if with_subtitles:
            try:
                txt = TextClip(
                    text=f'"{quote}"',
                    font_size=36,
                    color="white",
                    method="caption",
                    size=(int(1080 * 0.8), None),
                )
                txt = txt.with_position("center").with_duration(duration).crossfadein(1.5)  # type: ignore
                final_clip = CompositeVideoClip([clip, txt])
            except Exception as e:
                logger.warning(f"[Video] Subtitles failed (ImageMagick needed): {e}")
                final_clip = clip

        if audio_path and os.path.exists(audio_path):
            try:
                audio = AudioFileClip(audio_path)
                if audio.duration > duration:
                    audio = audio.subclipped(0, duration)  # type: ignore
                final_clip = final_clip.with_audio(audio)  # type: ignore
            except Exception as e:
                logger.warning(f"[Video] Audio attachment failed: {e}")

        # ── Step 5: Export ────────────────────────────────────────────────
        fd, output_path = tempfile.mkstemp(suffix=".mp4", prefix="levi_video_")
        os.close(fd)
        tmp_files.append(output_path)

        final_clip.write_videofile(
            output_path,
            fps=24,
            codec="libx264",
            audio_codec="aac",
            logger=None,
        )

        with open(output_path, "rb") as f:
            video_data = f.read()

        logger.info(f"[Video] Generated: {len(video_data)} bytes")
        video_output = BytesIO(video_data)
    finally:
        for path in tmp_files:
            try:
                if path and os.path.exists(str(path)):
                    os.remove(str(path))
            except Exception:
                pass

    return video_output

# Alias
generate_video = generate_quote_video