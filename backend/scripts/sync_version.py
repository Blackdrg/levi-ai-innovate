import os

# --- Sovereign Graduation: Universal Version Sync Script ---
TARGET_VERSION = "v14.0.0-Autonomous-SOVEREIGN"
LEGACY_VERSION = "v1.0.0-RC1"
EXTENSIONS = {".md", ".py", ".conf", ".json", ".js", ".jsx"}
PROJECT_ROOT = "d:/LEVI-AI"

def sync_versions():
    updated_files = 0
    replacement_count = 0
    
    for root, dirs, files in os.walk(PROJECT_ROOT):
        # Skip virtual environments and hidden git folders
        if ".venv" in root or ".git" in root or ".gemini" in root:
            continue
            
        for file in files:
            if any(file.endswith(ext) for ext in EXTENSIONS):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    if LEGACY_VERSION in content:
                        new_content = content.replace(LEGACY_VERSION, TARGET_VERSION)
                        replacements = content.count(LEGACY_VERSION)
                        
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write(new_content)
                        
                        updated_files += 1
                        replacement_count += replacements
                        print(f"✅ Updated: {file_path} ({replacements} replacements)")
                except Exception as e:
                    print(f"❌ Error updating {file_path}: {e}")

    print("\n--- Graduation Sync Complete ---")
    print(f"Total Files Updated: {updated_files}")
    print(f"Total Replacements: {replacement_count}")

if __name__ == "__main__":
    sync_versions()
