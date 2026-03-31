import subprocess
import os
import time

def run_server_test():
    """
    Validation script for the backend server lifecycle.
    """
    env = os.environ.copy()
    # Aligning paths with the current workspace v6.8
    workspace = os.getcwd()
    env["PYTHONPATH"] = workspace
    env["PYTHONUNBUFFERED"] = "1"

    print(f"Starting backend from {workspace}...")
    with open("server_log.txt", "w") as log_file:
        try:
            # We use 'python -m uvicorn' to ensure we use the current venv's uvicorn
            process = subprocess.Popen(
                [sys.executable, "-m", "uvicorn", "backend.main:app", "--host", "127.0.0.1", "--port", "8000"],
                env=env,
                stdout=log_file,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )

            time.sleep(10) # Reduced for CI/CD collection speed
            if process.poll() is not None:
                print(f"Process terminated with exit code {process.returncode}")
            else:
                print("Process started successfully. Terminating for test completion.")
                process.terminate()
        except Exception as e:
            print(f"Failed to launch server: {e}")

if __name__ == "__main__":
    import sys
    run_server_test()
