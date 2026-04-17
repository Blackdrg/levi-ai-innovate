import uvicorn
import os
import sys
from multiprocessing import freeze_support

# Ensure we can import from the parent directory if running in dev
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if __name__ == "__main__":
    freeze_support()
    # Import app here to avoid issues with freeze_support
    from backend.main import app
    
    port = int(os.environ.get("LEVI_BACKEND_PORT", 8000))
    print(f"Starting LEVI-AI Backend on port {port}...")
    uvicorn.run(app, host="127.0.0.1", port=port, workers=1)
