import os
def read_env_full():
    # Path relative to project root (.env is in root, this script is in tmp/)
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path = os.path.join(project_root, ".env")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            for i, line in enumerate(lines):
                print(f"{i+1}: {line.strip()}")
    else:
        print("File not found.")

if __name__ == "__main__":
    read_env_full()
