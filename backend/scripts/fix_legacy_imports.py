import os

REPLACEMENTS = {
    "from backend.db.firestore_db": "from backend.db.firestore_db",
    "import backend.db.firestore_db": "import backend.db.firestore_db",
    "backend.db.firestore_db": "backend.db.firestore_db",

    "from backend.db.redis_client": "from backend.db.redis_client",
    "import backend.db.redis_client": "import backend.db.redis_client",
    "backend.db.redis_client": "backend.db.redis_client",

    "from backend.services.learning.logic": "from backend.services.learning.logic",
    "import backend.services.learning.logic": "import backend.services.learning.logic",
    
    "from backend.services.learning.models": "from backend.services.learning.models",
    "import backend.services.learning.models": "import backend.services.learning.models",

    "from backend.services.image_gen": "from backend.services.image_gen",
    "from backend.services.notifications.logic": "from backend.services.notifications.logic",

    "from backend.celery_app ": "from backend.celery_app ",
    "from backend.core.agent_registry": "from backend.core.agent_registry",
    
    "from backend.services.learning.trainer": "from backend.services.learning.trainer",
    "from backend.services.studio.utils": "from backend.services.studio.utils",
    "from backend.services.video_gen": "from backend.services.video_gen",
}

def fix_imports(root_dir):
    count = 0
    for subdir, _, files in os.walk(root_dir):
        for f in files:
            if not f.endswith(".py"): continue
            # Skip the script itself or decommissioned files if you want,
            # but replacing in them is harmless anyway.
            path = os.path.join(subdir, f)
            try:
                with open(path, "r", encoding="utf-8") as file:
                    content = file.read()
                
                original = content
                for old, new in REPLACEMENTS.items():
                    content = content.replace(old, new)
                
                if content != original:
                    with open(path, "w", encoding="utf-8") as file:
                        file.write(content)
                    print(f"[OK] Fixed imports in: {path}")
                    count += 1
            except Exception as e:
                print(f"[SKIP] {path}: {e}")
                
    print(f"\n✅ Successfully replaced legacy imports in {count} files.")

if __name__ == "__main__":
    fix_imports(r"c:\Users\mehta\Desktop\New folder\LEVI-AI\backend")
