import os

files = [
    'backend/video_gen.py',
    'backend/trainer.py',
    'backend/image_gen.py',
    'backend/generation.py',
    'backend/content_engine.py'
]

for f in files:
    if os.path.exists(f):
        with open(f, 'r', encoding='utf-8') as file:
            data = file.read()
        
        updated_data = data.replace('llama3-8b-8192', 'llama-3.1-8b-instant')
        
        with open(f, 'w', encoding='utf-8') as file:
            file.write(updated_data)
        print(f"Fixed {f}")
