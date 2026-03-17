import subprocess
import os
import time

env = os.environ.copy()
env["PYTHONPATH"] = "C:/Users/mehta/Desktop/LEVI"
env["PYTHONUNBUFFERED"] = "1"

print("Starting backend with subprocess...")
with open("server_log.txt", "w") as log_file:
    process = subprocess.Popen(
        ["C:/Users/mehta/Desktop/LEVI/venv/Scripts/python.exe", "-m", "uvicorn", "backend.main:app", "--host", "127.0.0.1", "--port", "8000", "--log-level", "debug"],
        env=env,
        stdout=log_file,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )

    time.sleep(30)
    if process.poll() is not None:
        print(f"Process terminated with exit code {process.returncode}")
    else:
        print("Process is still running.")
