import sys
import os
sys.path.insert(0, os.getcwd())

from backend.gateway import app

print("Registered Routes:")
for route in app.routes:
    if hasattr(route, "path"):
        print(f"{route.methods} {route.path}")
