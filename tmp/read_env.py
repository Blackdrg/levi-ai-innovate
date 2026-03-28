import os
def read_env_full():
    path = r"c:\Users\mehta\Desktop\New folder\LEVI-AI\.env"
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            for i, line in enumerate(lines):
                print(f"{i+1}: {line.strip()}")
    else:
        print("File not found.")

if __name__ == "__main__":
    read_env_full()
