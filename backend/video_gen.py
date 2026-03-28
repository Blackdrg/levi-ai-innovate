# pyright: reportMissingImports=false
"""
LEVI Video Generation Engine v3.0
- Multi-scene composition with smooth transitions
- Real Ken Burns zoom/pan effects
- Coqui TTS narration with fallback
- Subtitle overlay with proper font rendering
- Background ambient music mixing
- Groq-powered narration script
- 9:16 vertical (Reels) and 16:9 landscape modes
"""

import os
import uuid
import logging
import tempfile
import random
from io import BytesIO
from typing import Optional, Any, List, Tuple

from backend.utils.network import safe_request, standard_retry, DEFAULT_TIMEOUT
from backend.circuit_breaker import groq_breaker

logger = logging.getLogger(__name__)

# ── Dependency Availability Checks ──
HAS_MOVIEPY = False
HAS_TTS = False
HAS_NUMPY = False

from backend.firestore_db import db as firestore_db  # type: ignore
from backend.redis_client import cache_search, get_cached_search, HAS_REDIS  # type: ignore
from backend.embeddings import embed_text  # type: ignore
from backend.s3_utils import upload_to_s3  # type: ignore

try:
    import numpy as np  # type: ignore
    HAS_NUMPY = True
except ImportError:
    pass

try:
    try:
        from moviepy import (  # type: ignore
            ImageClip, TextClip, CompositeVideoClip,
            AudioFileClip, concatenate_videoclips, ColorClip,
        )
        from moviepy.video.fx import fadein, fadeout  # type: ignore
    except ImportError:
        from moviepy.editor import (  # type: ignore
            ImageClip, TextClip, CompositeVideoClip,
            AudioFileClip, concatenate_videoclips, ColorClip,
        )
    HAS_MOVIEPY = True
except ImportError:
    logger.warning("MoviePy not installed. Video generation unavailable.")

try:
    from TTS.api import TTS as CoquiTTS  # type: ignore
    HAS_TTS = True
except ImportError:
    pass


# ─────────────────────────────────────────────
# SCRIPT GENERATION (Groq-powered)
# ─────────────────────────────────────────────

@standard_retry
def generate_narration_script(quote: str, author: str, mood: str,
                               style: str = "reflective") -> str:
    """Generate a rich narration script using Groq with retries."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return f'"{quote}" — {author}'

    script_styles = {
        "reflective": "contemplative, slow, with pauses. Let each word breathe.",
        "dramatic": "with rising intensity, building to a peak on the key insight.",
        "intimate": "as if speaking to one person in a quiet room. Personal, close.",
        "documentary": "like a nature documentary narrator — measured, authoritative.",
    }

    style_instruction = script_styles.get(style, script_styles["reflective"])

    try:
        resp = groq_breaker.call(
            safe_request,
            "POST",
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": "llama-3.1-8b-instant",
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You write narration scripts for short philosophical video clips. "
                            f"Write {style_instruction} "
                            "Structure: brief intro (5 words max) → read the quote → closing reflection (1 sentence). "
                            "Total: 30-50 words. Output ONLY the narration text, no stage directions."
                        )
                    },
                    {
                        "role": "user",
                        "content": f'Quote: "{quote}"\nAuthor: {author}\nMood: {mood}'
                    }
                ],
                "max_tokens": 100,
                "temperature": 0.75,
            },
            timeout=DEFAULT_TIMEOUT
        )
        if resp.status_code == 200:
            return resp.json()["choices"][0]["message"]["content"].strip()
        elif resp.status_code == 429:
            logger.warning("Groq rate limited during script generation.")
            raise requests.exceptions.RequestException("Rate limited")
        else:
            resp.raise_for_status()
    except Exception as e:
        logger.warning(f"Script generation failed: {e}")
        raise # Reraise to trigger Tenacity retry

    return f"{quote} — {author}"


# ─────────────────────────────────────────────
# TTS ENGINE
# ─────────────────────────────────────────────

_tts_engine: Any = None
_tts_lock = __import__('threading').Lock()


def _get_tts() -> Optional[Any]:
    """Lazy-load Coqui TTS."""
    global _tts_engine
    if not HAS_TTS:
        return None
    if _tts_engine is not None:
        return _tts_engine

    with _tts_lock:
        if _tts_engine is not None:
            return _tts_engine
        try:
            _tts_engine = CoquiTTS(
                model_name="tts_models/en/ljspeech/tacotron2-DDC",
                progress_bar=False
            )
            logger.info("[TTS] Coqui engine loaded")
            return _tts_engine
        except Exception as e:
            logger.error(f"[TTS] Failed to load: {e}")
            return None


def synthesize_speech(text: str) -> Optional[str]:
    """Convert text to speech WAV file. Returns file path or None."""
    tts = _get_tts()
    if not tts:
        return None
    try:
        fd, path = tempfile.mkstemp(suffix=".wav", prefix="levi_tts_")
        os.close(fd)
        tts.tts_to_file(text=text, file_path=path)
        logger.info(f"[TTS] Generated: {path}")
        return path
    except Exception as e:
        logger.error(f"[TTS] Synthesis failed: {e}")
        return None


# ─────────────────────────────────────────────
# VISUAL EFFECTS
# ─────────────────────────────────────────────

def apply_ken_burns(clip: Any, duration: float,
                    zoom_start: float = 1.0, zoom_end: float = 1.12,
                    direction: str = "in") -> Any:
    """
    Apply smooth Ken Burns zoom+pan effect.
    direction: 'in', 'out', 'left', 'right', 'diagonal'
    """
    if not HAS_NUMPY:
        return clip

    w, h = clip.size

    pan_vectors = {
        "in":       (0.0, 0.0),
        "out":      (0.0, 0.0),
        "left":     (-0.03, 0.0),
        "right":    (0.03, 0.0),
        "diagonal": (0.02, -0.02),
        "up":       (0.0, -0.03),
    }
    pan = pan_vectors.get(direction, (0.0, 0.0))

    def zoom_effect(get_frame, t: float):
        from PIL import Image as PILImage  # type: ignore
        progress = t / max(duration, 0.001)

        if direction == "out":
            zoom = zoom_end - (zoom_end - zoom_start) * progress
        else:
            zoom = zoom_start + (zoom_end - zoom_start) * progress

        frame = get_frame(t)
        img = PILImage.fromarray(frame)

        new_w = int(w * zoom)
        new_h = int(h * zoom)
        img = img.resize((new_w, new_h), PILImage.Resampling.LANCZOS)

        # Pan offset
        pan_x = int(pan[0] * w * progress)
        pan_y = int(pan[1] * h * progress)
        left = (new_w - w) // 2 + pan_x
        top = (new_h - h) // 2 + pan_y

        # Clamp
        left = max(0, min(left, new_w - w))
        top = max(0, min(top, new_h - h))

        img = img.crop((left, top, left + w, top + h))
        return np.array(img)

    try:
        return clip.transform(zoom_effect)
    except Exception as e:
        logger.warning(f"Ken Burns failed: {e}")
        return clip


def create_transition_clip(size: Tuple[int, int], duration: float = 0.5,
                            color: Tuple = (0, 0, 0)) -> Any:
    """Create a fade-to-black transition clip."""
    return ColorClip(size, color=color).with_duration(duration)


# ─────────────────────────────────────────────
# SUBTITLE RENDERER
# ─────────────────────────────────────────────

def create_subtitle_clip(text: str, size: Tuple[int, int],
                          duration: float, mood: str = "neutral") -> Any:
    """Create a styled subtitle overlay."""
    accent_colors = {
        "inspiring": "rgb(242,202,80)",
        "cyberpunk": "rgb(200,100,255)",
        "zen": "rgb(100,200,120)",
        "stoic": "rgb(200,180,140)",
        "philosophical": "rgb(140,160,255)",
    }
    accent = accent_colors.get(mood.lower(), "white")
    W, H = size

    try:
        txt_clip = TextClip(
            text=f'"{text}"',
            font_size=min(44, max(28, int(W * 0.038))),
            color="white",
            method="caption",
            size=(int(W * 0.82), None),
            stroke_color="black",
            stroke_width=2,
        )
        y_pos = int(H * 0.72)
        txt_clip = txt_clip.with_position(("center", y_pos)).with_duration(duration)

        # Fade in/out
        txt_clip = txt_clip.crossfadein(0.8).crossfadeout(0.5)  # type: ignore
        return txt_clip
    except Exception as e:
        logger.warning(f"TextClip failed: {e}")
        return None


# ─────────────────────────────────────────────
# MULTI-SCENE PIPELINE
# ─────────────────────────────────────────────

def _split_into_scenes(script: str, num_scenes: int = 3) -> List[str]:
    """Split script text into scenes for multi-image generation."""
    sentences = []
    for s in script.replace("!", ".").replace("?", ".").split("."):
        s = s.strip()
        if s:
            sentences.append(s)

    if not sentences:
        return [script] * num_scenes

    # Distribute evenly
    bucket_size = max(1, len(sentences) // num_scenes)
    scenes = []
    for i in range(num_scenes):
        start = i * bucket_size
        end = start + bucket_size if i < num_scenes - 1 else len(sentences)
        segment = sentences[start:end]
        scenes.append(". ".join(segment) + ".")

    return scenes


def generate_scene_image(prompt: str, mood: str, size: Tuple[int, int]) -> Any:
    """Generate a single scene background image as numpy array."""
    if not HAS_NUMPY:
        raise ImportError("numpy required for video generation")

    try:
        try:
            from backend.image_gen import generate_via_together, generate_gradient_fallback  # type: ignore
        except ImportError:
            from image_gen import generate_via_together, generate_gradient_fallback  # type: ignore

        if os.getenv("TOGETHER_API_KEY"):
            try:
                pil_img = generate_via_together(prompt, size)
                return np.array(pil_img.convert("RGB"))
            except Exception:
                pass

        # Fallback to gradient
        pil_img = generate_gradient_fallback(mood, size)
        return np.array(pil_img.convert("RGB"))

    except Exception as e:
        logger.error(f"Scene image generation failed: {e}")
        # Ultra fallback: solid color
        return np.zeros((size[1], size[0], 3), dtype=np.uint8)


# ─────────────────────────────────────────────
# MAIN ENTRY POINTS
# ─────────────────────────────────────────────

def generate_quote_video(
    quote: str,
    author: str = "",
    mood: str = "neutral",
    user_tier: str = "free",
    bg_music: Optional[str] = None,
    with_narration: bool = True,
    with_subtitles: bool = True,
    aspect_ratio: str = "9:16",
    num_scenes: int = 3,
) -> BytesIO:
    """
    Full video composition pipeline.
    Returns MP4 as BytesIO.

    aspect_ratio: '9:16' (vertical/Reels) or '16:9' (landscape)
    """
    if not HAS_MOVIEPY:
        raise ImportError("MoviePy is required. Install: pip install moviepy")
    if not HAS_NUMPY:
        raise ImportError("numpy is required for video generation")

    # Size configuration
    if aspect_ratio == "16:9":
        size = (1920, 1080)
    else:
        size = (1080, 1920)  # 9:16 vertical

    tmp_files = []
    scene_clips = []
    warnings = []

    try:
        # ── Step 1: Generate narration script ──
        narration_text = quote
        if with_narration:
            narration_text = generate_narration_script(quote, author, mood)

        # ── Step 2: Split into scenes ──
        scene_texts = _split_into_scenes(narration_text, num_scenes)
        scene_duration = max(4.0, min(8.0, 20.0 / num_scenes))

        # ── Step 3: Build image prompt ──
        try:
            try:
                from backend.image_gen import build_prompt  # type: ignore
            except ImportError:
                from image_gen import build_prompt  # type: ignore
            base_prompt = build_prompt(quote, mood, enhance=True)
        except Exception:
            base_prompt = f"{mood} atmosphere, cinematic, high quality"

        # ── Step 4: Generate scene clips ──
        kb_directions = ["in", "out", "left", "right", "diagonal", "up"]

        for i, scene_text in enumerate(scene_texts):
            logger.info(f"[Video] Scene {i+1}/{num_scenes}")
            try:
                scene_prompt = f"{base_prompt}, {scene_text[:50]}"
                img_array = generate_scene_image(scene_prompt, mood, size)

                clip = ImageClip(img_array).with_duration(scene_duration)

                # Randomize Ken Burns direction per scene
                direction = kb_directions[i % len(kb_directions)]
                clip = apply_ken_burns(clip, scene_duration,
                                       zoom_start=1.0, zoom_end=1.1,
                                       direction=direction)

                # Cross-fade in (not first clip)
                if i > 0:
                    clip = clip.crossfadein(0.8)  # type: ignore

                scene_clips.append(clip)

            except Exception as e:
                logger.warning(f"[Video] Scene {i+1} failed: {e}")
                # Blank fallback clip
                blank = ColorClip(size, color=(10, 10, 20)).with_duration(scene_duration)
                scene_clips.append(blank)

        if not scene_clips:
            raise RuntimeError("All scenes failed to generate")

        # ── Step 5: Concatenate scenes ──
        final_clip = concatenate_videoclips(scene_clips, method="compose")
        total_duration = sum(scene_duration for _ in scene_clips)

        # ── Step 6: Subtitle overlay ──
        if with_subtitles:
            subtitle = create_subtitle_clip(quote, size, total_duration * 0.85, mood)
            if subtitle:
                offset = total_duration * 0.1
                subtitle = subtitle.with_start(offset)  # type: ignore
                final_clip = CompositeVideoClip([final_clip, subtitle])

        # ── Step 7: TTS Audio ──
        audio_path = None
        if with_narration and HAS_TTS:
            audio_path = synthesize_speech(narration_text)
            if audio_path:
                tmp_files.append(audio_path)

        if audio_path and os.path.exists(audio_path):
            try:
                audio = AudioFileClip(audio_path)
                if audio.duration > total_duration:
                    audio = audio.subclipped(0, total_duration)  # type: ignore
                final_clip = final_clip.with_audio(audio)  # type: ignore
            except Exception as e:
                logger.warning(f"[Video] Audio attachment failed: {e}")

        # Background music
        if bg_music and os.path.exists(bg_music):
            try:
                music = AudioFileClip(bg_music)
                if music.duration > total_duration:
                    music = music.subclipped(0, total_duration)  # type: ignore
                music = music.with_volume_scaled(0.12)  # type: ignore

                if final_clip.audio:
                    from moviepy import CompositeAudioClip  # type: ignore
                    final_clip = final_clip.with_audio(
                        CompositeAudioClip([final_clip.audio, music])
                    )
                else:
                    final_clip = final_clip.with_audio(music)  # type: ignore
            except Exception as e:
                logger.warning(f"[Video] Background music failed: {e}")

        # ── Step 8: Export ──
        fd, output_path = tempfile.mkstemp(suffix=".mp4", prefix="levi_video_")
        os.close(fd)
        tmp_files.append(output_path)

        final_clip.write_videofile(
            output_path,
            fps=24,
            codec="libx264",
            audio_codec="aac",
            bitrate="2000k",
            threads=2,
            logger=None,
        )

        with open(output_path, "rb") as f:
            video_data = f.read()

        logger.info(f"[Video] Generated: {len(video_data)} bytes")
        return {"data": BytesIO(video_data), "engine": "moviepy_together", "success": True, "warnings": warnings}

    except Exception as e:
        logger.error(f"[Video] Generation failed: {e}")
        return {"data": None, "engine": "moviepy", "success": False, "warnings": warnings + [str(e)]}
    finally:
        for path in tmp_files:
            try:
                if path and os.path.exists(str(path)):
                    os.remove(str(path))
            except Exception:
                pass


def generate_video(
    quote: str,
    author: str = "",
    mood: str = "neutral",
    **kwargs
) -> BytesIO:
    """Public alias for generate_quote_video."""
    return generate_quote_video(quote, author, mood, **kwargs)


def generate_reel(quote: str, author: str = "", mood: str = "neutral") -> BytesIO:
    """Generate a short Instagram Reel (15-30 second, 9:16)."""
    return generate_quote_video(
        quote, author, mood,
        aspect_ratio="9:16",
        num_scenes=2,
        with_narration=True,
        with_subtitles=True,
    )
