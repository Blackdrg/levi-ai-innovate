import os
import json
import mimetypes

ROOT_DIR = r"d:\LEVI-AI"

EXTENSIONS = {
    # Source Code
    "py": "Python",
    "js": "JavaScript",
    "ts": "TypeScript",
    "tsx": "TypeScript",
    "jsx": "JavaScript",
    "rs": "Rust",
    "go": "Go",
    "c": "C",
    "cpp": "C++",
    "h": "C/C++",
    "hpp": "C++",
    "java": "Java",
    "kt": "Kotlin",
    "swift": "Swift",
    "dart": "Dart",
    "rb": "Ruby",
    "php": "PHP",
    "html": "HTML",
    "css": "CSS",
    "scss": "SCSS",
    "sass": "SASS",
    # Config
    "json": "JSON",
    "yaml": "YAML",
    "yml": "YAML",
    "toml": "TOML",
    "ini": "INI",
    "env": "ENV",
    # Documentation
    "md": "Markdown",
    "txt": "Text",
    # Scripts
    "sh": "Shell",
    "bash": "Shell",
    "bat": "Batch",
    "ps1": "PowerShell",
    # Database
    "sql": "SQL",
}

DEPENDENCY_PATH_KEYWORDS = ["node_modules", "site-packages", "vendor", "venv", ".venv", "__pycache__", ".git", ".pytest_cache", ".ruff_cache", "pip"]

def get_category(path, ext):
    path_lower = path.lower()
    
    # Dependencies
    for keyword in DEPENDENCY_PATH_KEYWORDS:
        if f"\\{keyword}\\" in path_lower or f"/{keyword}/" in path_lower or path_lower.endswith(f"\\{keyword}") or path_lower.endswith(f"/{keyword}"):
            # Special check for .git
            if ".git" in path_lower and not any(k in path_lower for k in ["node_modules", "venv", ".venv"]):
                pass # .git is often excluded but we must include everything per instructions
            return "Dependencies"

    # Specific Infra/DevOps
    infra_files = ["dockerfile", "docker-compose", "kubernetes", "prometheus.yml", "nginx.conf", "firebase.json", "firestore.rules", "vercel.json"]
    if any(k in os.path.basename(path).lower() for k in infra_files) or ".github" in path_lower:
        return "Infra/DevOps"

    if ext in ["py", "js", "ts", "tsx", "jsx", "rs", "go", "c", "cpp", "h", "hpp", "java", "kt", "swift", "dart", "rb", "php", "html", "css", "scss", "sass", "sql"]:
        return "Source Code"
    
    if ext in ["json", "yaml", "yml", "toml", "ini"] or os.path.basename(path).startswith(".env"):
        return "Config Files"
    
    if ext in ["md", "txt"]:
        return "Documentation"
    
    if ext in ["sh", "bat", "ps1"]:
        return "Scripts"
    
    if ext in ["log", "bak", "dat", "dir"]:
        return "Logs/Generated"
    
    return "Other"

def count_lines(file_path):
    try:
        # Check if it's likely binary
        # We'll try to read a small chunk to detect null bytes
        with open(file_path, "rb") as f:
            chunk = f.read(1024)
            if b"\x00" in chunk:
                return None # Binary
        
        # Count lines
        count = 0
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            for _ in f:
                count += 1
        return count
    except Exception:
        return None

def analyze():
    stats = {
        "global": {"files": 0, "lines": 0},
        "categories": {},
        "languages": {},
        "top_files": [],
        "directories": {},
        "binary_files": []
    }

    for root, dirs, files in os.walk(ROOT_DIR):
        # Major Directory Breakdown
        rel_root = os.path.relpath(root, ROOT_DIR)
        major_dir = rel_root.split(os.sep)[0] if rel_root != "." else "root"
        
        if major_dir not in stats["directories"]:
            stats["directories"][major_dir] = {"files": 0, "lines": 0}

        for file in files:
            file_path = os.path.join(root, file)
            stats["global"]["files"] += 1
            
            ext = file.split(".")[-1].lower() if "." in file else ""
            lang = EXTENSIONS.get(ext, "Other")
            category = get_category(file_path, ext)
            
            line_count = count_lines(file_path)
            
            if line_count is not None:
                stats["global"]["lines"] += line_count
                
                # Category stats
                if category not in stats["categories"]:
                    stats["categories"][category] = {"files": 0, "lines": 0}
                stats["categories"][category]["files"] += 1
                stats["categories"][category]["lines"] += line_count
                
                # Language stats
                if lang not in stats["languages"]:
                    stats["languages"][lang] = {"files": 0, "lines": 0}
                stats["languages"][lang]["files"] += 1
                stats["languages"][lang]["lines"] += line_count
                
                # Directory stats
                stats["directories"][major_dir]["files"] += 1
                stats["directories"][major_dir]["lines"] += line_count
                
                # Top files
                stats["top_files"].append({"path": os.path.relpath(file_path, ROOT_DIR), "lines": line_count})
                stats["top_files"].sort(key=lambda x: x["lines"], reverse=True)
                stats["top_files"] = stats["top_files"][:20]
            else:
                # Binary file
                size = os.path.getsize(file_path)
                stats["binary_files"].append({
                    "name": os.path.relpath(file_path, ROOT_DIR),
                    "size": size,
                    "reason": "Binary or Encoding Issue"
                })

    return stats

if __name__ == "__main__":
    results = analyze()
    print(json.dumps(results, indent=2))
