
import os
import re

FRONTEND_DIR = "frontend"

def check_html_file(file_path):
    print(f"\n--- Checking {file_path} ---")
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    errors = []
    
    # 1. Check for standard meta tags
    if '<meta charset="UTF-8">' not in content:
        errors.append("Missing <meta charset='UTF-8'>")
    if 'name="viewport"' not in content:
        errors.append("Missing <meta name='viewport'>")
    if 'name="theme-color"' not in content:
        errors.append("Missing <meta name='theme-color'>")
    
    # 2. Check for PWA manifest
    if 'link rel="manifest" href="manifest.json"' not in content:
        errors.append("Missing manifest.json link")
    
    # 3. Check for external assets (local)
    scripts = re.findall(r'script src="([^"]+)"', content)
    links = re.findall(r'link rel="stylesheet" href="([^"]+)"', content)
    
    for script in scripts:
        if not script.startswith('http') and not os.path.exists(os.path.join(FRONTEND_DIR, script)):
            errors.append(f"Broken script link: {script}")
            
    for link in links:
        if not link.startswith('http') and not os.path.exists(os.path.join(FRONTEND_DIR, link)):
            errors.append(f"Broken stylesheet link: {link}")

    # 4. Check internal navigation links (only local relative paths)
    # This regex now ignores absolute URLs (http/https)
    nav_links = re.findall(r'href="([^"h][^"]+\.html)"', content)
    for link in nav_links:
        # Ignore external links
        if link.startswith('http'):
            continue
        if not os.path.exists(os.path.join(FRONTEND_DIR, link)):
            errors.append(f"Broken navigation link: {link}")

    if not errors:
        print("✅ No errors found.")
        return True
    else:
        for error in errors:
            print(f"❌ {error}")
        return False

if __name__ == "__main__":
    html_files = [f for f in os.listdir(FRONTEND_DIR) if f.endswith('.html')]
    all_passed = True
    for file in html_files:
        if not check_html_file(os.path.join(FRONTEND_DIR, file)):
            all_passed = False
            
    print("\n" + "="*30)
    print(f"Final HTML Validation: {'PASSED' if all_passed else 'FAILED'}")
    print("="*30)
