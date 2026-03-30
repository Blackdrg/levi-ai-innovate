import subprocess
import os
import sys
import time
from dotenv import load_dotenv

if os.path.exists(".env.local"):
    load_dotenv(".env.local")
else:
    load_dotenv()

# Kill existing
def kill_port(port):
    if os.name == 'nt':
        cmd = f'netstat -ano | findstr LISTENING | findstr :{port}'
        try:
            output = subprocess.check_output(cmd, shell=True).decode()
            for line in output.splitlines():
                if f':{port}' in line:
                    pid = line.strip().split()[-1]
                    if pid != '0':
                        subprocess.run(f'taskkill /F /PID {pid}', shell=True, capture_output=True)
        except Exception: pass

kill_port(8000)
time.sleep(2)

env = os.environ.copy()
root_dir = os.getcwd()
backend_dir = os.path.join(root_dir, "backend")
env["PYTHONPATH"] = f"{root_dir};{backend_dir}"

with open("server_debug.log", "w") as f:
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"],
        env=env,
        stdout=f,
        stderr=subprocess.STDOUT
    )
    print("Server started. PID:", proc.pid)
    try:
         while True: time.sleep(1)
    except KeyboardInterrupt:
         proc.terminate()
