from PIL import Image, ImageDraw, ImageFont, ImageFilter
import requests
from io import BytesIO
import os
import random
import textwrap
import re
import base64
import math

def get_keywords_from_quote(quote: str, mood: str = "") -> str:
    """Extracts visually descriptive keywords from the quote and mood."""
    # 1. Stop words to ignore
    stop_words = {"the", "a", "an", "is", "are", "was", "were", "to", "for", "in", "on", "at", "by", "with", "from", "and", "or", "but", "not", "no", "yes", "my", "your", "his", "her", "their", "our", "it", "this", "that", "these", "those", "of", "be", "been", "being", "have", "has", "had", "do", "does", "did", "can", "could", "shall", "should", "will", "would", "may", "might", "must"}
    
    # 2. Extract words, clean them, and filter
    words = re.findall(r'\b\w+\b', quote.lower())
    meaningful_words = [w for w in words if w not in stop_words and len(w) > 3]
    
    # 3. Mood-based keywords
    mood_keywords = {
        'inspiring': 'light,dawn,mountain,soaring',
        'calm': 'serene,lake,zen,forest',
        'energetic': 'abstract,storm,dynamic,fire',
        'philosophical': 'stars,galaxy,nebula,infinite',
        'melancholic': 'rain,fog,solitude,muted',
        'stoic': 'sculpture,marble,peak,monolith',
        'zen': 'bamboo,stones,ripple,garden',
        'cyberpunk': 'neon,glitch,vibrant,city',
        'futuristic': 'technology,digital,geometry,void'
    }
    
    base_keywords = mood_keywords.get(mood.lower(), 'abstract,artistic')
    
    # 4. Combine: take top 2 words from quote and add mood keywords
    if meaningful_words:
        # Sort by length as a proxy for "meaningful" if no NLP is available
        meaningful_words.sort(key=len, reverse=True)
        top_words = meaningful_words[:3]
        return f"{base_keywords},{','.join(top_words)}"
    
    return base_keywords

def generate_quote_image(quote: str, author: str = "", mood: str = "", size: tuple = (1080, 1080), custom_bg: str = None) -> BytesIO:
    """Generates an artistic quote image with open-source backgrounds or custom uploads."""
    
    # 1. Fetch or Load Background
    bg_img = None
    
    if custom_bg:
        try:
            if custom_bg.startswith('data:image'):
                header, encoded = custom_bg.split(",", 1)
                data = base64.b64decode(encoded)
                bg_img = Image.open(BytesIO(data)).convert('RGBA')
            elif custom_bg.startswith('http'):
                resp = requests.get(custom_bg, timeout=5)
                bg_img = Image.open(BytesIO(resp.content)).convert('RGBA')
            
            if bg_img:
                if bg_img.size != size:
                    bg_img = bg_img.resize(size, Image.Resampling.LANCZOS)
                # Add overlay for custom images too
                overlay_opacity = 140
                overlay = Image.new('RGBA', size, (0, 0, 0, overlay_opacity))
                bg_img = Image.alpha_composite(bg_img, overlay)
        except Exception as e:
            print(f"Warning: Failed to load custom background: {e}")
            bg_img = None

    if bg_img is None:
        keywords = get_keywords_from_quote(quote, mood)
        
        # Try multiple sources
        bg_urls = [
            f"https://loremflickr.com/{size[0]}/{size[1]}/{keywords}/all",
            f"https://picsum.photos/seed/{random.randint(0, 1000)}/{size[0]}/{size[1]}",
            f"https://source.unsplash.com/featured/{size[0]}x{size[1]}?{keywords.replace(',', '+')}"
        ]
        
        for url in bg_urls:
            try:
                resp = requests.get(url, timeout=5)
                if resp.status_code == 200:
                    bg_img = Image.open(BytesIO(resp.content)).convert('RGBA')
                    # Resize if necessary to maintain consistent sizing
                    if bg_img.size != size:
                        bg_img = bg_img.resize(size, Image.Resampling.LANCZOS)
                    
                    # Dynamic Dark Overlay based on mood
                    overlay_opacity = 160 if mood.lower() in ['philosophical', 'melancholic', 'cyberpunk'] else 130
                    overlay = Image.new('RGBA', size, (0, 0, 0, overlay_opacity))
                    bg_img = Image.alpha_composite(bg_img, overlay)
                    break
            except Exception as e:
                print(f"Warning: Failed to fetch background from {url}: {e}")
                continue

    # 2. Base Gradient (Fallback if background fetch fails)
    if bg_img is None:
        mood_colors = {
            'inspiring': [(40, 0, 80), (100, 40, 180)],
            'calm': [(10, 40, 50), (40, 120, 130)],
            'energetic': [(80, 0, 20), (200, 60, 40)],
            'philosophical': [(20, 20, 20), (60, 60, 80)],
            'melancholic': [(5, 10, 30), (30, 40, 100)],
            'stoic': [(30, 30, 30), (100, 100, 100)],
            'zen': [(40, 50, 20), (120, 140, 60)],
            'cyberpunk': [(20, 0, 40), (255, 0, 180)],
            'futuristic': [(0, 10, 40), (0, 255, 255)]
        }
        colors = mood_colors.get(mood.lower(), [(20, 30, 50), (60, 80, 120)])
        base = Image.new('RGBA', size, colors[0] + (255,))
        top = Image.new('RGBA', size, colors[1] + (255,))
        mask = Image.new('L', size)
        mask_draw = ImageDraw.Draw(mask)
        for y in range(size[1]):
            mask_draw.line([(0, y), (size[0], y)], fill=int(255 * (y / size[1])))
        bg_img = Image.composite(top, base, mask)
    
    draw = ImageDraw.Draw(bg_img, 'RGBA')
    
    # 3. Add Artistic "Star/Noise" Overlay (only if no background)
    if bg_img.getextrema()[3][0] == 255: # If opaque (likely gradient)
        for _ in range(300):
            x, y = random.randint(0, size[0]), random.randint(0, size[1])
            r = random.randint(1, 3)
            opacity = random.randint(50, 200)
            draw.ellipse([x-r, y-r, x+r, y+r], fill=(255, 255, 255, opacity))

    # 3. Add Abstract Artistic Shapes
    for _ in range(5):
        x1, y1 = random.randint(0, size[0]), random.randint(0, size[1])
        x2, y2 = x1 + random.randint(100, 400), y1 + random.randint(100, 400)
        draw.rectangle([x1, y1, x2, y2], outline=(255, 255, 255, 20), width=2)
        draw.ellipse([x1, y1, x2, y2], outline=(255, 255, 255, 10), width=1)

    # 4. Stylized Typography
    try:
        # Define font styles based on mood
        mood_fonts = {
            'stoic': ["georgiab.ttf", "timesbd.ttf", "DejaVuSerif-Bold.ttf"],
            'cyberpunk': ["arialbd.ttf", "verdana.ttf", "DejaVuSans-Bold.ttf"],
            'zen': ["georgia.ttf", "times.ttf", "DejaVuSerif.ttf"],
            'energetic': ["impact.ttf", "arialbd.ttf", "DejaVuSans-Bold.ttf"],
            'melancholic': ["georgia.ttf", "times.ttf", "DejaVuSerif.ttf"]
        }
        
        # Try to find a font that matches the mood
        preferred_fonts = mood_fonts.get(mood.lower(), ["georgia.ttf", "arial.ttf", "DejaVuSerif.ttf"])
        
        font_paths = [
            "C:\\Windows\\Fonts\\", 
            "/usr/share/fonts/truetype/dejavu/",
            "/System/Library/Fonts/Supplemental/"
        ]
        
        font_path = None
        for pf in preferred_fonts:
            for bp in font_paths:
                full_path = os.path.join(bp, pf)
                if os.path.exists(full_path):
                    font_path = full_path
                    break
            if font_path: break
            
        if font_path:
            # Dynamic font size based on quote length
            base_size = 82 if len(quote) < 100 else 64
            if len(quote) > 200: base_size = 52
            
            font_quote = ImageFont.truetype(font_path, base_size)
            font_author = ImageFont.truetype(font_path, int(base_size * 0.6))
        else:
            font_quote = ImageFont.load_default()
            font_author = ImageFont.load_default()
    except Exception as e:
        print(f"Font loading error: {e}")
        font_quote = ImageFont.load_default()
        font_author = ImageFont.load_default()

    # Text Wrapping & Spacing
    char_per_line = 22 if len(quote) > 150 else 28
    if len(quote) < 50: char_per_line = 20
    
    wrapper = textwrap.TextWrapper(width=char_per_line)
    lines = wrapper.wrap(text=quote)
    
    # Dynamic vertical spacing based on font size
    line_h = font_quote.getbbox("Ay")[3] - font_quote.getbbox("Ay")[1] if hasattr(font_quote, 'getbbox') else 80
    line_spacing = int(line_h * 1.3)
    author_margin = 120
    total_h = len(lines) * line_spacing + author_margin
    start_y = (size[1] - total_h) / 2
    
    # 5. Draw Quote with better aesthetics
    for i, line in enumerate(lines):
        # Use getbbox for accurate centering
        if hasattr(draw, 'textbbox'):
            bbox = draw.textbbox((0, 0), line, font=font_quote)
            w = bbox[2] - bbox[0]
        else:
            w = draw.textlength(line, font=font_quote) if hasattr(draw, 'textlength') else 500
            
        curr_y = start_y + i * line_spacing
        
        # Multi-layered shadow for depth
        shadow_offsets = [(1, 1), (2, 2), (3, 3)]
        for ox, oy in shadow_offsets:
            draw.text(((size[0]-w)/2 + ox, curr_y + oy), line, fill=(0, 0, 0, 60), font=font_quote)
        
        # Main text
        draw.text(((size[0]-w)/2, curr_y), line, fill=(255, 255, 255, 255), font=font_quote)
    
    # 6. Draw Author with artistic flair
    author_text = f"— {author}" if author else "— LEVI AI"
    if hasattr(draw, 'textbbox'):
        abbox = draw.textbbox((0, 0), author_text, font=font_author)
        aw = abbox[2] - abbox[0]
    else:
        aw = draw.textlength(author_text, font=font_author) if hasattr(draw, 'textlength') else 200
        
    author_y = start_y + len(lines) * line_spacing + 60
    
    # Stylish accent line
    accent_w = 80
    draw.line([(size[0]/2 - accent_w/2, author_y - 15), (size[0]/2 + accent_w/2, author_y - 15)], fill=(255, 255, 255, 100), width=2)
    
    draw.text(((size[0]-aw)/2, author_y), author_text, fill=(255, 255, 255, 200), font=font_author)
    
    # 7. Enhanced Border and Overlays
    # Vignette effect
    vignette = Image.new('RGBA', size, (0, 0, 0, 0))
    v_draw = ImageDraw.Draw(vignette)
    for i in range(180):
        alpha = int(100 * (1 - i/180))
        v_draw.rectangle([i, i, size[0]-i, size[1]-i], outline=(0, 0, 0, alpha), width=1)
    bg_img = Image.alpha_composite(bg_img, vignette)
    
    # Artistic "Dust & Scratches" overlay
    dust = Image.new('RGBA', size, (0, 0, 0, 0))
    d_draw = ImageDraw.Draw(dust)
    for _ in range(150):
        x, y = random.randint(0, size[0]), random.randint(0, size[1])
        r = random.randint(1, 2)
        d_draw.ellipse([x-r, y-r, x+r, y+r], fill=(255, 255, 255, random.randint(10, 40)))
    
    for _ in range(10):
        x1, y1 = random.randint(0, size[0]), random.randint(0, size[1])
        length = random.randint(10, 30)
        angle = random.uniform(0, 3.14)
        x2 = x1 + length * math.cos(angle)
        y2 = y1 + length * math.sin(angle)
        d_draw.line([(x1, y1), (x2, y2)], fill=(255, 255, 255, 20), width=1)
    bg_img = Image.alpha_composite(bg_img, dust)

    # Final Border
    draw = ImageDraw.Draw(bg_img, 'RGBA')
    draw.rectangle([40, 40, size[0]-40, size[1]-40], outline=(255, 255, 255, 40), width=2)
    draw.rectangle([55, 55, size[0]-55, size[1]-55], outline=(255, 255, 255, 15), width=1)
    
    # Final artistic filter
    bg_img = bg_img.filter(ImageFilter.SHARPEN)
    bg_img = bg_img.filter(ImageFilter.SMOOTH_MORE)
    
    bio = BytesIO()
    bg_img.save(bio, 'PNG', optimize=True)
    bio.seek(0)
    return bio


