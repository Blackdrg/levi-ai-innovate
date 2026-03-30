import os
import glob
import re

html_files = glob.glob("frontend/*.html")

# The replacement script
firebase_scripts = """<script src="https://www.gstatic.com/firebasejs/10.8.1/firebase-app-compat.js"></script>
<script src="https://www.gstatic.com/firebasejs/10.8.1/firebase-auth-compat.js"></script>
<script src="js/auth-manager.js"></script>"""

for file in html_files:
    if "auth (1).html" in file:
        continue

    with open(file, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Prevent double injection
    if "firebase-app-compat.js" not in content:
        content = content.replace('<script src="js/auth-manager.js"></script>', firebase_scripts)
        
        with open(file, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Injected Firebase SDK into {file}")

print("Firebase SDK injection complete!")
