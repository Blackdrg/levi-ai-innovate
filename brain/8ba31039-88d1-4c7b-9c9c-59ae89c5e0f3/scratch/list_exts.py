import os
from collections import Counter

def list_extensions(path):
    exts = Counter()
    for root, dirs, files in os.walk(path):
        for f in files:
            _, ext = os.path.splitext(f)
            exts[ext.lower()] += 1
    return exts

if __name__ == "__main__":
    exts = list_extensions("d:\\LEVI-AI")
    for ext, count in exts.most_common():
        print(f"{ext}: {count}")
