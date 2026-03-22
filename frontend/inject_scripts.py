import glob
import os

files = glob.glob(r'c:\Users\mehta\Desktop\New folder\LEVI-AI\frontend\*.html')
for file in files:
    with open(file, 'r', encoding='utf-8') as f:
        content = f.read()
    if 'js/animations.js' not in content:
        content = content.replace('</body>', '<script src="js/animations.js" type="module"></script>\n<script src="js/feedback.js" type="module"></script>\n</body>')
        with open(file, 'w', encoding='utf-8') as f:
            f.write(content)
print(f"Injected scripts into {len(files)} files.")
