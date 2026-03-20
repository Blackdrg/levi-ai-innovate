from PIL import Image, ImageDraw, ImageFont
import requests
from io import BytesIO
import os

# Environment check
RENDER = os.getenv("RENDER") == "true"

def add_watermark(img, user_tier="free"):
    if user_tier == "free":
        draw = ImageDraw.Draw(img)
        width, height = img.size
        # Bottom right: "Made with LEVI AI"
        try:
            font_tiny = ImageFont.truetype("arial.ttf", 16)
        except:
            font_tiny = ImageFont.load_default()
        
        text = "Made with LEVI AI"
        bbox = draw.textbbox((0, 0), text, font=font_tiny)
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        draw.text((width - w - 20, height - h - 20), text, fill=(255, 255, 255, 128), font=font_tiny)
    return img

def generate_quote_image(quote: str, author: str = "", mood: str = "", size: tuple = (800, 400), user_tier: str = "free", return_pil: bool = False) -> BytesIO:
    """
    Generates a stylized quote image using PIL.
    NOTE: This is a synchronous, CPU-bound blocking operation. 
    Always call this in a ThreadPoolExecutor if using inside an async FastAPI route.
    """
    # Mood bg
    mood_colors = {
        'happy': (255, 193, 7),
        'sad': (33, 150, 243),
        'motivational': (76, 175, 80),
        'calm': (156, 39, 176),
        'success': (255, 152, 0),
    }
    bg_color = mood_colors.get(mood.lower(), (100, 100, 120))
    img = Image.new('RGB', size, color=bg_color)
    draw = ImageDraw.Draw(img)
    
    # Font (fallback)
    try:
        font_large = ImageFont.truetype("arial.ttf", 36)
        font_small = ImageFont.truetype("arial.ttf", 24)
    except:
        font_large = ImageFont.load_default()
        font_small = ImageFont.load_default()
    
    # Quote text
    bbox = draw.textbbox((0,0), quote, font=font_large)
    w = bbox[2] - bbox[0]
    draw.text(((size[0]-w)/2, 100), quote, fill=(255,255,255), font=font_large)
    
    # Author
    bbox = draw.textbbox((0,0), author, font=font_small)
    w = bbox[2] - bbox[0]
    draw.text(((size[0]-w)/2, 250), f"— {author}", fill=(255,255,255, 128), font=font_small)
    
    # Apply Watermark
    img = add_watermark(img, user_tier)

    if return_pil:
        return img

    bio = BytesIO()
    img.save(bio, 'PNG')
    bio.seek(0)
    return bio
