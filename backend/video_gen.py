# pyright: reportMissingImports=false
from typing import Optional
try:
    from moviepy import ImageClip, TextClip, CompositeVideoClip, AudioFileClip  # type: ignore
    HAS_MOVIEPY = True
except ImportError:
    HAS_MOVIEPY = False

try:
    from backend.image_gen import generate_quote_image  # type: ignore
except ImportError:
    from image_gen import generate_quote_image  # type: ignore
from io import BytesIO
import os
import logging

logger = logging.getLogger(__name__)

def generate_quote_video(quote: str, author: str, mood: str, user_tier: str = "free", bg_music: Optional[str] = None):
    """
    Generates an 8-second MP4 video for the quote.
    """
    if not HAS_MOVIEPY:
        logger.error("MoviePy is not installed. Video generation is unavailable.")
        raise ImportError("MoviePy not installed. Please install moviepy and ImageMagick.")

    try:
        # 1. Generate the image
        img_pil = generate_quote_image(quote, author, mood, user_tier=user_tier, return_pil=True)
        
        # Convert PIL image to numpy array for MoviePy
        import numpy as np  # type: ignore
        img_array = np.array(img_pil)
        
        # 2. Create the base clip
        # MoviePy v2.x uses with_duration, with_position, etc.
        # If linter still complains, we cast to Any or ignore as types might be outdated
        clip = ImageClip(img_array).with_duration(8) # type: ignore
        
        # 3. Add text animation (MoviePy requires ImageMagick for TextClip)
        try:
            # MoviePy v2.x: font_size instead of fontsize
            txt = TextClip(text=quote, font_size=40, color='white', method='caption', size=(img_pil.size[0]*0.8, None)) \
                .with_position('center') \
                .with_duration(8) \
                .crossfadein(1) # type: ignore
            final_clip = CompositeVideoClip([clip, txt])
        except Exception as e:
            logger.warning(f"TextClip failed (likely ImageMagick missing): {e}. Using static image clip.")
            final_clip = clip

        # 4. Add ambient music (royalty-free)
        if bg_music and os.path.exists(bg_music):
            try:
                # MoviePy v2.x: subclipped instead of subclip, with_audio instead of set_audio
                audio = AudioFileClip(bg_music).subclipped(0, 8) # type: ignore
                final_clip = final_clip.with_audio(audio) # type: ignore
            except Exception as e:
                logger.error(f"Failed to add audio: {e}")
        
        # 5. Export as MP4
        output_path = f"temp_video_{os.urandom(4).hex()}.mp4"
        final_clip.write_videofile(output_path, fps=24, codec="libx264", audio_codec="aac")
        
        with open(output_path, "rb") as f:
            video_data = f.read()
        
        # Clean up
        os.remove(output_path)
        
        return BytesIO(video_data)
        
    except Exception as e:
        logger.error(f"Video generation failed: {e}")
        raise e
