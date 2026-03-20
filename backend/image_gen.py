from PIL import Image, ImageDraw, ImageFont
import requests
from io import BytesIO
import os

import os

# Environment check
RENDER = os.getenv("RENDER") == "true"

def generate_quote_image(quote: str, author: str = "", mood: str = "", size: tuple = (800, 400)) -> BytesIO:
    """
    Generates a stylized quote image using PIL.
    NOTE: This is a synchronous, CPU-bound blocking operation. 
    Always call this in a ThreadPoolExecutor if using inside an async FastAPI route.
    On Render Free Tier, we keep it simple to save RAM.
    """
    # 1. Very simple base if on Render
    if RENDER:
        img = Image.new('RGB', size, color=(30, 30, 40))
    else:
        # Slightly more complex or dynamic background logic here
        img = Image.new('RGB', size, color=(20, 30, 50))
    draw = ImageDraw.Draw(img)
    
    # Font (fallback)
    try:
        font_large = ImageFont.truetype("arial.ttf", 36)
        font_small = ImageFont.truetype("arial.ttf", 24)
    except:
        font_large = ImageFont.load_default()
        font_small = ImageFont.load_default()
    
    # Mood bg
    mood_colors = {
        'happy': (255, 193, 7),
        'sad': (33, 150, 243),
        'motivational': (76, 175, 80),
        'calm': (156, 39, 176),
        'success': (255, 152, 0),
        'sad': (33, 150, 243)
    }
    bg_color = mood_colors.get(mood.lower(), (100, 100, 120))
    img = Image.new('RGB', size, color=bg_color)
    draw = ImageDraw.Draw(img)
    
    # Quote text
    bbox = draw.textbbox((0,0), quote, font=font_large)
    w = bbox[2] - bbox[0]
    h = bbox[3] - bbox[1]
    draw.text(((size[0]-w)/2, 50), quote, fill=(255,255,255), font=font_large)
    
    # Author
    bbox = draw.textbbox((0,0), author, font=font_small)
    w = bbox[2] - bbox[0]
    draw.text(((size[0]-w)/2, 250), f"— {author}", fill=(255,255,255, 128), font=font_small)
    
    bio = BytesIO()
    img.save(bio, 'PNG')
    bio.seek(0)
    return bio

# HF stub for advanced
# from diffusers import StableDiffusionPipeline
# pipe = StableDiffusionPipeline.from_pretrained("CompVis/stable-diffusion-v1-4")
# image = pipe("abstract quote background mood happy").images[0]

