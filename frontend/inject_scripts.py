import glob
import os

# Get the directory of the current script (frontend/)
script_dir = os.path.dirname(os.path.abspath(__file__))
files = glob.glob(os.path.join(script_dir, '*.html'))
for file in files:
    with open(file, 'r', encoding='utf-8') as f:
        content = f.read()
    if 'js/animations.js' not in content:
        content = content.replace('</body>', '<script src="js/animations.js" type="module"></script>\n<script src="js/feedback.js" type="module"></script>\n</body>')
        with open(file, 'w', encoding='utf-8') as f:
            f.write(content)
print(f"Injected scripts into {len(files)} files.")
