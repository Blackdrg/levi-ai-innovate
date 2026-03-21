import os
import re

def fix_html_files():
    frontend_dir = "frontend"
    if not os.path.exists(frontend_dir):
        print(f"Error: {frontend_dir} directory not found.")
        return

    # Metadata and PWA tags to ensure are present
    required_tags = [
        '<meta charset="UTF-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1.0">',
        '<meta name="theme-color" content="#09090f">',
        '<link rel="manifest" href="manifest.json">',
        '<meta name="apple-mobile-web-app-capable" content="yes">',
        '<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">',
        '<link rel="apple-touch-icon" href="icon-192.png">'
    ]

    html_files = [f for f in os.listdir(frontend_dir) if f.endswith(".html")]
    
    for filename in html_files:
        filepath = os.path.join(frontend_dir, filename)
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        original_content = content
        
        # Ensure <head> exists
        if "<head>" not in content:
            content = content.replace("<html>", "<html>\n<head>")
            if "</head>" not in content:
                # Close head before body if missing
                content = content.replace("<body>", "</head>\n<body>")

        # Check and insert missing tags
        head_match = re.search(r"<head>(.*?)</head>", content, re.DOTALL | re.IGNORECASE)
        if head_match:
            head_inner = head_match.group(1)
            new_tags = []
            for tag in required_tags:
                # Check for tag existence (simplified check)
                tag_name = tag.split()[0].replace("<", "")
                if tag_name == "meta":
                    # Check specific meta name or charset
                    if 'charset' in tag:
                        if 'charset' not in head_inner: new_tags.append(tag)
                    else:
                        name_match = re.search(r'name=["\'](.*?)["\']', tag)
                        if name_match:
                            name = name_match.group(1)
                            if f'name="{name}"' not in head_inner and f"name='{name}'" not in head_inner:
                                new_tags.append(tag)
                elif tag_name == "link":
                    rel_match = re.search(r'rel=["\'](.*?)["\']', tag)
                    if rel_match:
                        rel = rel_match.group(1)
                        if f'rel="{rel}"' not in head_inner and f"rel='{rel}'" not in head_inner:
                            new_tags.append(tag)

            if new_tags:
                inserted_tags = "\n    " + "\n    ".join(new_tags)
                content = content.replace("<head>", f"<head>{inserted_tags}")
                print(f"✅ Fixed {filename}: Added {len(new_tags)} missing tags.")
            else:
                print(f"ℹ️ {filename} already has all required tags.")
        
        if content != original_content:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)

if __name__ == "__main__":
    print("--- Fixing HTML Metadata & PWA Tags ---")
    fix_html_files()
    print("--- Done ---")
