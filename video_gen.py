"""
video_gen.py — Safe video generation with graceful fallback if moviepy/ffmpeg missing.
"""
import os
import logging
from io import BytesIO

logger = logging.getLogger(__name__)

# ── Safe moviepy import ────────────────────────────────────────────────────────
try:
    try:
        from moviepy import ImageClip, TextClip, CompositeVideoClip, AudioFileClip
    except ImportError:
        from moviepy.editor import ImageClip, TextClip, CompositeVideoClip, AudioFileClip
    HAS_MOVIEPY = True
    logger.info("MoviePy loaded successfully.")
except ImportError:
    HAS_MOVIEPY = False
    logger.warning("MoviePy not installed — video generation will be unavailable.")

try:
    from backend.image_gen import generate_quote_image
except ImportError:
    from image_gen import generate_quote_image


def generate_quote_video(
    quote: str,
    author: str,
    mood: str,
    user_tier: str = "free",
    bg_music: str = None
) -> BytesIO:
    """
    Generates an 8-second MP4 video for the quote.
    Requires MoviePy + ffmpeg installed in the container.
    Raises RuntimeError with a clear message if dependencies are missing.
    """
    if not HAS_MOVIEPY:
        raise RuntimeError(
            "Video generation requires moviepy and ffmpeg. "
            "Install with: pip install moviepy  and  apt-get install ffmpeg"
        )

    try:
        import numpy as np

        # 1. Generate the background image as a PIL Image (use return_pil=True)
        img_pil = generate_quote_image(
            quote, author, mood,
            user_tier=user_tier,
            return_pil=True          # returns PIL Image, not BytesIO
        )

        # 2. Convert PIL → numpy array (MoviePy needs RGB array)
        img_array = np.array(img_pil.convert("RGB"))

        # 3. Create base video clip from the image
        clip = ImageClip(img_array).set_duration(8)

        # 4. Optionally overlay animated text (needs ImageMagick)
        final_clip = clip
        try:
            txt = (
                TextClip(
                    quote,
                    fontsize=40,
                    color="white",
                    method="caption",
                    size=(int(img_pil.size[0] * 0.8), None),
                )
                .set_position("center")
                .set_duration(8)
                .crossfadein(1)
            )
            final_clip = CompositeVideoClip([clip, txt])
        except Exception as e:
            logger.warning(f"TextClip skipped (ImageMagick missing?): {e}")

        # 5. Add optional background music
        if bg_music and os.path.exists(bg_music):
            try:
                audio = AudioFileClip(bg_music).subclip(0, 8)
                final_clip = final_clip.set_audio(audio)
            except Exception as e:
                logger.error(f"Audio attach failed: {e}")

        # 6. Export to a temp file then read bytes
        tmp_path = f"/tmp/levi_video_{os.urandom(4).hex()}.mp4"
        final_clip.write_videofile(
            tmp_path,
            fps=24,
            codec="libx264",
            audio_codec="aac",
            logger=None,           # suppress moviepy progress bar
        )

        with open(tmp_path, "rb") as f:
            video_data = f.read()

        # Clean up temp file
        try:
            os.remove(tmp_path)
        except OSError:
            pass

        return BytesIO(video_data)

    except Exception as e:
        logger.error(f"Video generation failed: {e}", exc_info=True)
        raise
