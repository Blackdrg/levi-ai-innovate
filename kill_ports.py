import os
import subprocess
import socket
import time
import sys

def _port_free(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("127.0.0.1", port)) != 0

def kill_port(port: int):
    if os.name == "nt":
        try:
            print(f"[*] Checking port {port}...")
            out = subprocess.check_output(
                f'netstat -ano | findstr LISTENING | findstr :{port}',
                shell=True, text=True, stderr=subprocess.DEVNULL
            )
            found = False
            for line in out.splitlines():
                if f":{port}" in line:
                    found = True
                    pid = line.strip().split()[-1]
                    if pid.isdigit() and pid != "0":
                        print(f"[!] Killing process {pid} on port {port}...")
                        subprocess.run(f"taskkill /F /PID {pid}",
                                       shell=True, capture_output=True)
            if not found:
                print(f"[OK] Port {port} is already free.")
        except subprocess.CalledProcessError:
            print(f"[OK] Port {port} is already free.")
        except Exception as e:
            print(f"[ERROR] Failed to kill port {port}: {e}")
    else:
        try:
            print(f"[*] Port {port}: Killing processes...")
            subprocess.run(f"lsof -ti:{port} | xargs kill -9",
                           shell=True, capture_output=True)
        except Exception as e:
            print(f"[ERROR] Failed to kill port {port}: {e}")

def main():
    ports = [8000, 8080]
    if len(sys.argv) > 1:
        try:
            ports = [int(p) for p in sys.argv[1:]]
        except ValueError:
            print("Usage: python kill_ports.py [port1 port2 ...]")
            sys.exit(1)

    print("=" * 40)
    print("  LEVI Port Cleanup Utility")
    print("=" * 40)
    
    for port in ports:
        if not _port_free(port):
            kill_port(port)
            # Verify
            time.sleep(0.5)
            if _port_free(port):
                print(f"[SUCCESS] Port {port} is now free.")
            else:
                print(f"[FAILURE] Could not free port {port}.")
        else:
            print(f"[OK] Port {port} is already free.")
    
    print("=" * 40)
    print("Done.")

if __name__ == "__main__":
    main()
