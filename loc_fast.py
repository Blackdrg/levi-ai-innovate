import os
import time

def count_loc(dir_path):
    total_lines = 0
    file_count = 0
    start_time = time.time()
    
    # We will exclude extremely heavy binary directories and .git to save I/O overhead.
    # ALL exclusions removed. Counting everything including binaries and caches!
    exclude_dirs = set()
    
    print("Beginning absolute raw dependency and binary scan...")
    
    for root, dirs, files in os.walk(dir_path):
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        for file in files:
            file_path = os.path.join(root, file)
            
            try:
                # Fast counting via buffered chunk reads
                with open(file_path, "rb") as f:
                    lines = sum(1 for _ in f)
                    total_lines += lines
                    file_count += 1
                    
                    if file_count % 5000 == 0:
                        print(f"Still counting... Scanned {file_count:,} files (Current lines: {total_lines:,})", end='\r')
            except Exception:
                pass

    duration = time.time() - start_time
    print(" " * 80, end='\r') # clear the progress text
    print(f"\n✅ Total Files Scanned (Incl. Dependencies): {file_count:,}")
    print(f"✅ Total Absolute Lines of Code: {total_lines:,}")
    print(f"⏱️  Time taken: {duration:.2f} seconds\n")

if __name__ == "__main__":
    pwd = os.getcwd()
    print(f"Scanning directory: {pwd}")
    count_loc(pwd)
