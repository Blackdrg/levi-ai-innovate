
import subprocess
import sys
import os
import time
import signal
import socket

def is_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0

def kill_processes_on_ports(ports):
    for port in ports:
        if is_port_in_use(port):
            print(f"Port {port} is in use. Killing existing process...")
            if os.name == 'nt':
                # Windows
                try:
                    output = subprocess.check_output(f'netstat -ano | findstr :{port}', shell=True).decode()
                    for line in output.splitlines():
                        if 'LISTENING' in line:
                            pid = line.strip().split()[-1]
                            subprocess.run(f'taskkill /F /PID {pid}', shell=True)
                except:
                    pass
            else:
                # Linux/Mac
                subprocess.run(f'lsof -ti:{port} | xargs kill -9', shell=True)

def start_services():
    # 1. Kill any existing processes on 8000 and 8080
    kill_processes_on_ports([8000, 8080])

    # 2. Paths
    venv_python = os.path.join("venv", "Scripts", "python.exe") if os.name == 'nt' else os.path.join("venv", "bin", "python")
    if not os.path.exists(venv_python):
        venv_python = sys.executable

    print("--- Starting LEVI Backend (Port 8000) ---")
    backend_proc = subprocess.Popen(
        [venv_python, "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"],
    )

    print("--- Starting LEVI Frontend (Port 8080) ---")
    frontend_proc = subprocess.Popen(
        [venv_python, "-m", "http.server", "8080", "--bind", "0.0.0.0", "--directory", "frontend"],
    )

    try:
        while True:
            # Check if processes are still running
            if backend_proc.poll() is not None:
                print("Backend process died. Restarting...")
                backend_proc = subprocess.Popen([venv_python, "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"])
            
            if frontend_proc.poll() is not None:
                print("Frontend process died. Restarting...")
                frontend_proc = subprocess.Popen([venv_python, "-m", "http.server", "8080", "--directory", "frontend"])
            
            time.sleep(5)
    except KeyboardInterrupt:
        print("\nStopping services...")
        backend_proc.terminate()
        frontend_proc.terminate()
        sys.exit(0)

if __name__ == "__main__":
    start_services()
