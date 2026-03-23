# pyright: reportMissingImports=false
"""
Video Composer Pipeline for LEVI AI.

Pipeline: Text → Script (Groq) → Voice (Coqui TTS) → Image frames (SD) → Compose (MoviePy)
Features: Ken Burns zoom, crossfade transitions, subtitle overlay, ambient music.
Gated behind creator tier.
"""
import os
import uuid
import logging
import tempfile
from io import BytesIO
from typing import Optional, Any

logger = logging.getLogger(__name__)

# ── Dependency checks ──
HAS_MOVIEPY = False
HAS_TTS = False

try:
    from moviepy import (  # type: ignore
        ImageClip, TextClip, CompositeVideoClip,
        AudioFileClip, concatenate_videoclips,
    )
    HAS_MOVIEPY = True
except ImportError:
    try:
        from moviepy.editor import (  # type: ignore
            ImageClip, TextClip, CompositeVideoClip,
            AudioFileClip, concatenate_videoclips,
        )
        HAS_MOVIEPY = True
    except ImportError:
        pass

try:
    from TTS.api import TTS as CoquiTTS  # type: ignore
    HAS_TTS = True
except ImportError:
    pass


# ─────────────────────────────────────────────
# TTS: Text to Speech
# ─────────────────────────────────────────────
_tts_engine: Any = None


def _get_tts():
    """Lazy-load Coqui TTS engine."""
    global _tts_engine
    if _tts_engine is not None:
        return _tts_engine

    if not HAS_TTS:
        logger.warning("[TTS] Coqui TTS not installed. Audio will be skipped.")
        return None

    try:
        _tts_engine = CoquiTTS(model_name="tts_models/en/ljspeech/tacotron2-DDC", progress_bar=False)
        logger.info("[TTS] Coqui engine loaded (LJSpeech).")
        return _tts_engine
    except Exception as e:
        logger.error(f"[TTS] Failed to load: {e}")
        return None


def synthesize_speech(text: str) -> Optional[str]:
    """Convert text to speech. Returns path to WAV file or None."""
    tts = _get_tts()
    if not tts:
        return None

    try:
        fd, output_path = tempfile.mkstemp(suffix=".wav", prefix="levi_tts_")
        os.close(fd)
        tts.tts_to_file(text=text, file_path=output_path)
        logger.info(f"[TTS] Generated: {output_path}")
        return output_path
    except Exception as e:
        logger.error(f"[TTS] Synthesis failed: {e}")
        return None


# ─────────────────────────────────────────────
# Script Generator
# ─────────────────────────────────────────────
def generate_narration_script(quote: str, author: str, mood: str) -> str:
    """Use Groq to create a short narration script from a quote."""
    try:
        import groq  # type: ignore
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            return quote

        client = groq.Groq(api_key=api_key)
        response = client.chat.completions.create(
            model="llama3-8b-8192",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a narration scriptwriter. Given a quote with its author and mood, "
                        "create a brief, evocative narration that introduces the quote, reads it, "
                        "and closes with a reflective line. Keep it under 50 words total. "
                        "Output ONLY the narration text."
                    ),
                },
                {
                    "role": "user",
                    "content": f'Quote: "{quote}" — {author}\nMood: {mood}',
                },
            ],
            max_tokens=100,
            temperature=0.7,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.warning(f"[Script] Groq narration failed: {e}")
        return quote


# ─────────────────────────────────────────────
# Visual Effects
# ─────────────────────────────────────────────
def _apply_ken_burns(clip: Any, duration: float, zoom_ratio: float = 0.05) -> Any:
    """Apply a Ken Burns (slow zoom) effect to an image clip."""
    try:
        import numpy as np  # type: ignore
        from PIL import Image  # type: ignore

        w, h = clip.size

        def zoom_effect(get_frame, t):
            """Gradually zoom in over time."""
            progress = t / duration
            zoom = 1 + (zoom_ratio * progress)
            frame = get_frame(t)

            img = Image.fromarray(frame)
            new_w, new_h = int(w * zoom), int(h * zoom)
            img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)

            # Center crop back to original size
            left = (new_w - w) // 2
            top = (new_h - h) // 2
            img = img.crop((left, top, left + w, top + h))

            return np.array(img)

        return clip.transform(zoom_effect, apply_to="mask" if clip.mask else None)  # type: ignore
    except Exception as e:
        logger.warning(f"[KenBurns] Effect failed: {e}")
        return clip


# ─────────────────────────────────────────────
# Main Video Generation
# ─────────────────────────────────────────────
def generate_quote_video(
    quote: str,
    author: str,
    mood: str,
    user_tier: str = "free",
    bg_music: Optional[str] = None,
    with_narration: bool = True,
    with_subtitles: bool = True,
) -> BytesIO:
    """
    Full video composition pipeline.

    1. Generate background image via SD/Together
    2. Generate narration script via Groq
    3. Synthesize voice via Coqui TTS
    4. Compose with MoviePy (Ken Burns + subtitles + music)
    5. Return MP4 bytes
    """
    if not HAS_MOVIEPY:
        raise ImportError("MoviePy is required for video generation. Install with: pip install moviepy")

    tmp_files = []

    try:
        # ── Step 1: Background image ──
        try:
            from backend.image_gen import generate_quote_image  # type: ignore
        except ImportError:
            from image_gen import generate_quote_image  # type: ignore

        import numpy as np  # type: ignore

        img_pil = generate_quote_image(
            quote, author, mood,
            size=(1080, 1920),  # 9:16 vertical
            user_tier=user_tier,
            return_pil=True,
        )
        img_array = np.array(img_pil)

        duration = 10  # seconds
        clip = ImageClip(img_array).with_duration(duration)  # type: ignore

        # Apply Ken Burns zoom
        clip = _apply_ken_burns(clip, duration, zoom_ratio=0.04)

        # ── Step 2: Narration script ──
        narration_text = quote
        if with_narration:
            narration_text = generate_narration_script(quote, author, mood)

        # ── Step 3: TTS audio ──
        audio_path = None
        if with_narration and HAS_TTS:
            audio_path = synthesize_speech(narration_text)
            if audio_path:
                tmp_files.append(audio_path)

        # ── Step 4: Subtitles ──
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
                logger.warning(f"[Video] Subtitle overlay failed (ImageMagick?): {e}")
                final_clip = clip

        # ── Step 5: Attach audio ──
        if audio_path and os.path.exists(audio_path):
            try:
                audio = AudioFileClip(audio_path)
                # Match duration
                if audio.duration > duration:
                    audio = audio.subclipped(0, duration)  # type: ignore
                final_clip = final_clip.with_audio(audio)  # type: ignore
            except Exception as e:
                logger.warning(f"[Video] Audio attachment failed: {e}")

        # Ambient background music
        if bg_music and os.path.exists(bg_music):
            try:
                music = AudioFileClip(bg_music).subclipped(0, duration)  # type: ignore
                # Mix narration + music (lower music volume)
                music = music.with_volume_scaled(0.15)  # type: ignore
                if final_clip.audio:
                    from moviepy import CompositeAudioClip  # type: ignore
                    final_clip = final_clip.with_audio(
                        CompositeAudioClip([final_clip.audio, music])
                    )
                else:
                    final_clip = final_clip.with_audio(music)  # type: ignore
            except Exception as e:
                logger.warning(f"[Video] Background music failed: {e}")

        # ── Step 6: Export ──
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
        return BytesIO(video_data)

    except Exception as e:
        logger.error(f"[Video] Generation failed: {e}")
        raise

    finally:
        # Cleanup temp files
        for path in tmp_files:
            try:
                path_str = str(path) if path else ""
                if path_str and os.path.exists(path_str):
                    os.remove(path_str)
            except Exception:
                pass

    raise RuntimeError("Video generation exited unexpectedly")  # Pyre2 return-path guard


# ─────────────────────────────────────────────
# Multi-Scene Video Pipeline
# ─────────────────────────────────────────────
def _split_into_scenes(text: str, num_scenes: int = 3) -> list:
    """
    Split a script/narration into roughly equal scene segments.
    Each segment will get its own SD-generated background image.
    """
    sentences: list = [s.strip() for s in text.replace('!', '.').replace('?', '.').split('.') if s.strip()]
    if not sentences:
        return [text] * num_scenes

    # Distribute sentences into num_scenes buckets (Pyre2-safe: no list-slice)
    bucket_size = max(1, len(sentences) // num_scenes)
    scenes: list = []
    for i in range(num_scenes):
        start = i * bucket_size
        end = start + bucket_size if i < num_scenes - 1 else len(sentences)
        segment: list = [sentences[j] for j in range(start, end)]
        scenes.append('. '.join(segment) + '.')
    return scenes


def generate_multi_scene_video(
    script: str,
    mood: str = "neutral",
    user_tier: str = "free",
    num_scenes: int = 3,
    scene_duration: float = 6.0,
    bg_music: Optional[str] = None,
) -> BytesIO:
    """
    Advanced multi-scene video pipeline.

    1. Split script into scene segments
    2. Generate one SD image per scene segment
    3. Apply Ken Burns zoom to each scene clip
    4. Crossfade-concatenate all scene clips
    5. Attach TTS narration + optional background music
    6. Return MP4 bytes
    """
    if not HAS_MOVIEPY:
        raise ImportError("MoviePy is required for video generation.")

    try:
        import numpy as np  # type: ignore
    except ImportError:
        raise ImportError("numpy is required for video generation.")

    try:
        from backend.image_gen import generate_quote_image  # type: ignore
    except ImportError:
        from image_gen import generate_quote_image  # type: ignore

    tmp_files: list = []
    scene_texts = _split_into_scenes(script, num_scenes)
    clips = []

    for i, scene_text in enumerate(scene_texts):
        logger.info(f"[MultiScene] Generating scene {i+1}/{num_scenes}: '{scene_text[:50]}'")
        try:
            img_pil = generate_quote_image(
                scene_text, "", mood,
                size=(1080, 1920),
                user_tier=user_tier,
                return_pil=True,
            )
            img_array = np.array(img_pil)
            clip = ImageClip(img_array).with_duration(scene_duration)  # type: ignore
            clip = _apply_ken_burns(clip, scene_duration, zoom_ratio=0.04)

            # Add crossfade in (except first clip)
            if i > 0:
                clip = clip.crossfadein(1.0)  # type: ignore

            clips.append(clip)
        except Exception as e:
            logger.warning(f"[MultiScene] Scene {i+1} failed, using blank: {e}")

    if not clips:
        raise ValueError("All scenes failed to generate.")

    # Concatenate with crossfade composition
    final_clip = concatenate_videoclips(clips, method="compose")  # type: ignore
    total_duration = scene_duration * len(clips)

    # TTS narration for full script
    audio_path: Optional[str] = None
    if HAS_TTS:
        audio_path = synthesize_speech(script)
        if audio_path:
            tmp_files.append(audio_path)

    if audio_path and os.path.exists(audio_path):
        try:
            audio = AudioFileClip(audio_path)  # type: ignore
            if audio.duration > total_duration:
                audio = audio.subclipped(0, total_duration)  # type: ignore
            final_clip = final_clip.with_audio(audio)  # type: ignore
        except Exception as e:
            logger.warning(f"[MultiScene] Audio attachment failed: {e}")

    if bg_music and os.path.exists(bg_music):
        try:
            music = AudioFileClip(bg_music).subclipped(0, total_duration)  # type: ignore
            music = music.with_volume_scaled(0.15)  # type: ignore
            if final_clip.audio:
                from moviepy import CompositeAudioClip  # type: ignore
                final_clip = final_clip.with_audio(CompositeAudioClip([final_clip.audio, music]))
            else:
                final_clip = final_clip.with_audio(music)  # type: ignore
        except Exception as e:
            logger.warning(f"[MultiScene] Background music failed: {e}")

    fd, output_path = tempfile.mkstemp(suffix=".mp4", prefix="levi_multiscene_")
    os.close(fd)
    tmp_files.append(output_path)

    try:
        final_clip.write_videofile(
            output_path,
            fps=24,
            codec="libx264",
            audio_codec="aac",
            logger=None,
        )
        with open(output_path, "rb") as f:
            video_data = f.read()
        logger.info(f"[MultiScene] Generated {len(clips)}-scene video: {len(video_data)} bytes")
        return BytesIO(video_data)
    except Exception as e:
        logger.error(f"[MultiScene] Export failed: {e}")
        raise
    finally:
        for path in tmp_files:
            try:
                path_str = str(path) if path else ""
                if path_str and os.path.exists(path_str):
                    os.remove(path_str)
            except Exception:
                pass

    raise RuntimeError("Multi-scene video generation exited unexpectedly")  # Pyre2 return-path guard


# ─────────────────────────────────────────────
# Public alias
# ─────────────────────────────────────────────
def generate_video(
    quote: str,
    author: str = "",
    mood: str = "neutral",
    user_tier: str = "free",
    bg_music: Optional[str] = None,
    with_narration: bool = True,
    with_subtitles: bool = True,
) -> BytesIO:
    """
    Public alias for `generate_quote_video()`. Preferred entry point for external callers.
    """
    return generate_quote_video(
        quote, author, mood,
        user_tier=user_tier,
        bg_music=bg_music,
        with_narration=with_narration,
        with_subtitles=with_subtitles,
    )
