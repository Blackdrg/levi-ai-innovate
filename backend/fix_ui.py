import glob

files = glob.glob('frontend/**/*.html', recursive=True)
files += glob.glob('frontend/*.html')
files = list(set(files))

for f in files:
    print(f"Applying contrast fixes to {f}")
    with open(f, 'r', encoding='utf-8') as file:
        content = file.read()
    
    # 1. Restore dark background
    content = content.replace('bg-background', 'bg-surface')
    
    # 2. Increase label contrast (#69666e to #9ca3af)
    content = content.replace('#69666e', '#9ca3af')
    
    with open(f, 'w', encoding='utf-8') as file:
        file.write(content)

print("Batch Update Complete!")
