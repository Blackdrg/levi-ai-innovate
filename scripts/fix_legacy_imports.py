import os

mappings = {
    "backend.db.redis_client": "backend.db.redis",
    "backend.db.firestore_db": "backend.db.firebase",
    "backend.services.auth.logic": "backend.auth.logic",
    "backend.core.memory_manager": "backend.memory.manager",
    "backend.core.agents.": "backend.agents.",
    "backend.broadcast_utils": "backend.utils.broadcast"
}

def fix_imports(root_dir):
    print(f"Starting import cleanup in {root_dir}...")
    fixed_count = 0
    for root, dirs, files in os.walk(root_dir):
        for file in files:
            if file.endswith(".py") or file.endswith(".jsx") or file.endswith(".js"):
                path = os.path.join(root, file)
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        content = f.read()
                    
                    new_content = content
                    for old, new in mappings.items():
                        new_content = new_content.replace(old, new)
                    
                    if new_content != content:
                        with open(path, "w", encoding="utf-8") as f:
                            f.write(new_content)
                        fixed_count += 1
                        print(f"Fixed: {path}")
                except Exception as e:
                    print(f"Error processing {path}: {e}")
    print(f"Cleanup complete. Fixed {fixed_count} files.")

if __name__ == "__main__":
    # Get the project root directory (one level up from this script)
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    # Fix backend
    fix_imports(os.path.join(project_root, "backend"))
    # Fix frontend
    fix_imports(os.path.join(project_root, "frontend", "src"))
