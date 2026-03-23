# pyright: reportMissingImports=false

import subprocess
import sys
import os
import time
import signal
import socket
from dotenv import load_dotenv  # type: ignore

# Load local environment variables
if os.path.exists(".env.local"):
    load_dotenv(".env.local")
else:
    load_dotenv()

def is_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0

def kill_processes_on_ports(ports):
    for port in ports:
        print(f"Ensuring port {port} is free...")
        for _ in range(5):  # Try up to 5 times
            try:
                if os.name == 'nt':
                    # Windows: find all processes on this port
                    cmd = f'netstat -ano | findstr LISTENING | findstr :{port}'
                    output = subprocess.check_output(cmd, shell=True).decode()
                    found_any = False
                    for line in output.splitlines():
                        # Match :8000 exactly, e.g. 0.0.0.0:8000
                        if f':{port}' in line:
                            parts = line.strip().split()
                            if len(parts) >= 5:
                                pid = parts[-1]
                                if pid != '0':
                                    print(f"Killing process {pid} on port {port}...")
                                    subprocess.run(f'taskkill /F /PID {pid}', shell=True, capture_output=True)
                                    found_any = True
                    if not found_any:
                        break
                else:
                    # Linux/Mac
                    output = subprocess.check_output(f'lsof -ti:{port}', shell=True).decode()
                    if output:
                        print(f"Killing processes on port {port}...")
                        subprocess.run(f'lsof -ti:{port} | xargs kill -9', shell=True, capture_output=True)
                    else:
                        break
            except Exception:
                break
            time.sleep(1) # Wait for OS to clean up

def start_services():
    # 1. Kill any existing processes on 8000 and 8080
    kill_processes_on_ports([8000, 8080])
    
    # 2. Final check to ensure they are actually free
    for port in [8000, 8080]:
        while is_port_in_use(port):
            print(f"Waiting for port {port} to be released...")
            kill_processes_on_ports([port])
            time.sleep(2)

    # 2. Paths
    venv_python = os.path.join(".venv", "Scripts", "python.exe") if os.name == 'nt' else os.path.join(".venv", "bin", "python")
    if not os.path.exists(venv_python):
        venv_python = sys.executable

    print("--- Starting LEVI Backend (Port 8000) ---")
    # Add root and backend directories to PYTHONPATH
    env = os.environ.copy()
    root_dir = os.getcwd()
    backend_dir = os.path.join(root_dir, "backend")
    env["PYTHONPATH"] = f"{root_dir};{backend_dir}" if os.name == 'nt' else f"{root_dir}:{backend_dir}"
    
    backend_proc = subprocess.Popen(
        [venv_python, "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"],
        env=env
    )

    print("--- Starting LEVI Frontend (Port 8080) ---")
    frontend_proc = subprocess.Popen(
        [venv_python, "-m", "http.server", "8080", "--bind", "0.0.0.0", "--directory", "frontend"],
    )

    try:
        while True:
            # Check if processes are still running
            if backend_proc.poll() is not None:
                print("Backend process died. Waiting 5s before restart...")
                time.sleep(5)
                backend_proc = subprocess.Popen(
                    [venv_python, "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"],
                    env=env
                )
            
            if frontend_proc.poll() is not None:
                print("Frontend process died. Waiting 5s before restart...")
                time.sleep(5)
                frontend_proc = subprocess.Popen([venv_python, "-m", "http.server", "8080", "--directory", "frontend"])
            
            time.sleep(5)
    except KeyboardInterrupt:
        print("\nStopping services...")
        backend_proc.terminate()
        frontend_proc.terminate()
        sys.exit(0)

if __name__ == "__main__":
    start_services()
