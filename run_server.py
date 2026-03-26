import sys
import os
import subprocess
import socket
import time

def _port_free(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("127.0.0.1", port)) != 0

def _kill_port(port: int):
    if os.name == "nt":
        try:
            out = subprocess.check_output(
                f'netstat -ano | findstr LISTENING | findstr :{port}',
                shell=True, text=True, stderr=subprocess.DEVNULL
            )
            for line in out.splitlines():
                if f":{port}" in line:
                    pid = line.strip().split()[-1]
                    if pid.isdigit() and pid != "0":
                        subprocess.run(f"taskkill /F /PID {pid}",
                                       shell=True, capture_output=True)
        except Exception:
            pass
    else:
        try:
            subprocess.run(f"lsof -ti:{port} | xargs kill -9",
                           shell=True, capture_output=True)
        except Exception:
            pass

def _free_port(port: int):
    if not _port_free(port):
        print(f"[*] Port {port} is in use. Cleaning up...")
        _kill_port(port)
        for _ in range(5):
            time.sleep(0.5)
            if _port_free(port):
                break

try:
    import uvicorn
except ImportError:
    print("Uvicorn not found. Please install it with 'pip install uvicorn'.")
    exit(1)

if __name__ == "__main__":
    _free_port(8000)
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=False)
