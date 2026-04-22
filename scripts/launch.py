# scripts/launch.py
import subprocess
import time
import os
import sys

def launch():
    print("🚀 LEVI-AI Sovereign OS: Ignition Sequence...")
    
    # 1. Bootstrap the substrate
    print("🐘 [Bootstrap] Initializing Postgres and Redis...")
    subprocess.run([sys.executable, "scripts/bootstrap.py"], check=True)
    
    # 2. Start the Kernel Service (Background)
    print("⚡ [Kernel] Launching HAL-0 Native Runtime...")
    if os.name == 'nt':
        # Windows: Use start command
        kernel_proc = subprocess.Popen(["python", "backend/kernel/kernel_service.py"], 
                                      creationflags=subprocess.CREATE_NEW_CONSOLE)
    else:
        # Unix: Use nohup or &
        kernel_proc = subprocess.Popen(["python", "backend/kernel/kernel_service.py"], 
                                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    time.sleep(2) # Wait for port 8001
    
    # 3. Start the Mainframe (FastAPI)
    print("🧠 [Mainframe] Awakening the Soul...")
    try:
        subprocess.run(["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"], check=True)
    except KeyboardInterrupt:
        print("\n🛑 [Shutdown] Mission Aborted. Powering down Sovereign substrate...")
        kernel_proc.terminate()

if __name__ == "__main__":
    launch()
