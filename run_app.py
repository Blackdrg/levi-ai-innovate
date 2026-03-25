"""
LEVI - Single-command launcher
Starts: DB migrations -> Backend (FastAPI :8000) -> Frontend (static :8080)
Usage:  python run_app.py
        python run_app.py --no-migrate   (skip Alembic on fast restarts)
        python run_app.py --port-api 8000 --port-ui 8080
"""
# pyright: reportMissingImports=false

import subprocess
import sys
import os
import time
import socket
import argparse
import signal
import threading

# ─── CLI args ────────────────────────────────────────────────────────────────
parser = argparse.ArgumentParser(description="Run LEVI locally")
parser.add_argument("--no-migrate", action="store_true",
                    help="Skip Alembic migrations (faster restart)")
parser.add_argument("--no-seed", action="store_true",
                    help="Skip database seeding")
parser.add_argument("--port-api", type=int, default=8000)
parser.add_argument("--port-ui",  type=int, default=8080)
args = parser.parse_args()

API_PORT = args.port_api
UI_PORT  = args.port_ui

# ─── Resolve Python executable ───────────────────────────────────────────────
def _find_python():
    for candidate in [
        os.path.join(".venv", "Scripts", "python.exe"),   # Windows venv
        os.path.join(".venv", "bin", "python"),            # Unix venv
        os.path.join("venv",  "Scripts", "python.exe"),
        os.path.join("venv",  "bin", "python"),
        sys.executable,
    ]:
        if os.path.isfile(candidate):
            return os.path.abspath(candidate)
    return sys.executable

PYTHON = _find_python()
ROOT   = os.path.dirname(os.path.abspath(__file__))

# ─── Env setup ───────────────────────────────────────────────────────────────
def _load_env():
    """Load .env.local first, fall back to .env."""
    try:
        from dotenv import load_dotenv  # type: ignore
        for f in [".env.local", ".env"]:
            p = os.path.join(ROOT, f)
            if os.path.isfile(p):
                load_dotenv(p, override=False)
                print(f"[env] Loaded {f}")
                break
    except ImportError:
        # dotenv not installed — read manually for the critical keys
        for f in [".env.local", ".env"]:
            p = os.path.join(ROOT, f)
            if os.path.isfile(p):
                with open(p) as fh:
                    for line in fh:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            k, _, v = line.partition("=")
                            os.environ.setdefault(k.strip(), v.strip())
                print(f"[env] Loaded {f} (manual parse)")
                break

_load_env()

# Build PYTHONPATH so both `backend.X` and bare `X` imports work
backend_dir = os.path.join(ROOT, "backend")
env = os.environ.copy()
sep = ";" if os.name == "nt" else ":"
env["PYTHONPATH"] = sep.join(filter(None, [ROOT, backend_dir, env.get("PYTHONPATH", "")]))
env.setdefault("PYTHONUNBUFFERED", "1")
env.setdefault("DATABASE_URL", f"sqlite:///{ROOT}/levi_v2.db")

# ─── Port utilities ───────────────────────────────────────────────────────────
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

def _free_port(port: int, label: str):
    if not _port_free(port):
        print(f"[ports] Freeing port {port} ({label})...")
        _kill_port(port)
        for _ in range(10):
            time.sleep(0.5)
            if _port_free(port):
                break
        else:
            print(f"[ports] WARNING: could not free port {port}")

# ─── Backend health-check ─────────────────────────────────────────────────────
def _wait_for_backend(port: int, timeout: int = 60) -> bool:
    """Poll /health until the backend is ready or timeout expires."""
    import urllib.request
    import urllib.error
    url = f"http://127.0.0.1:{port}/health"
    deadline = time.time() + timeout
    dots = 0
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as r:
                if r.status == 200:
                    print()   # newline after dots
                    return True
        except Exception:
            pass
        print(".", end="", flush=True)
        dots += 1
        time.sleep(1)
    print()
    return False

# ─── Alembic migrations ───────────────────────────────────────────────────────
def _run_migrations():
    alembic_ini = os.path.join(backend_dir, "alembic.ini")
    if not os.path.isfile(alembic_ini):
        print("[migrate] alembic.ini not found — skipping migrations")
        return
    print("[migrate] Running Alembic migrations...")
    result = subprocess.run(
        [PYTHON, "-m", "alembic", "-c", alembic_ini, "upgrade", "head"],
        cwd=backend_dir,
        env=env,
    )
    if result.returncode != 0:
        print("[migrate] WARNING: migrations returned non-zero exit code")
    else:
        print("[migrate] [OK] Database schema up to date")

# ─── DB seed ──────────────────────────────────────────────────────────────────
def _run_seed():
    seed_script = os.path.join(backend_dir, "seed.py")
    if not os.path.isfile(seed_script):
        return
    print("[seed] Seeding database...")
    result = subprocess.run([PYTHON, seed_script], cwd=backend_dir, env=env)
    if result.returncode == 0:
        print("[seed] [OK] Done")
    else:
        print("[seed] WARNING: seed script returned non-zero (may be already seeded — OK)")

# ─── Process management ───────────────────────────────────────────────────────
processes: list = []

def _cleanup(*_):
    print("\n[shutdown] Stopping services…")
    for p in processes:
        try:
            p.terminate()
        except Exception:
            pass
    for p in processes:
        try:
            p.wait(timeout=5)
        except Exception:
            pass
    print("[shutdown] Done.")
    sys.exit(0)

signal.signal(signal.SIGINT,  _cleanup)
signal.signal(signal.SIGTERM, _cleanup)

# ─── Stream subprocess output ─────────────────────────────────────────────────
def _stream(proc, prefix: str):
    """Print subprocess stdout/stderr with a prefix tag."""
    def _read(stream, tag):
        try:
            for line in iter(stream.readline, b""):
                print(f"[{tag}] {line.decode(errors='replace').rstrip()}", flush=True)
        except Exception:
            pass
    threading.Thread(target=_read, args=(proc.stdout, prefix), daemon=True).start()
    threading.Thread(target=_read, args=(proc.stderr, prefix + "-err"), daemon=True).start()

# ─── Main ─────────────────────────────────────────────────────────────────────
def main():
    print("=" * 50)
    print("  LEVI - Local Launcher")
    print(f"  API  -> http://localhost:{API_PORT}")
    print(f"  UI   -> http://localhost:{UI_PORT}")
    print("=" * 50)

    # 1. Free ports
    _free_port(API_PORT, "API")
    _free_port(UI_PORT,  "UI")

    # 2. Migrations + seed (before the backend starts)
    if not args.no_migrate:
        _run_migrations()
    if not args.no_seed:
        _run_seed()

    # 3. Start FastAPI backend
    print(f"\n[api] Starting FastAPI on :{API_PORT}...")
    api_proc = subprocess.Popen(
        [
            PYTHON, "-m", "uvicorn", "backend.main:app",
            "--host", "0.0.0.0",
            "--port", str(API_PORT),
            "--reload",                    # hot-reload for development
            "--reload-dir", backend_dir,
        ],
        cwd=ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    processes.append(api_proc)
    _stream(api_proc, "api")

    # 4. Wait until the backend is actually ready
    print(f"[api] Waiting for backend to be ready", end="", flush=True)
    ready = _wait_for_backend(API_PORT, timeout=60)
    if not ready:
        print(f"[api] ERROR: backend did not start within 60 s. Check logs above.")
        _cleanup()
    print(f"[api] [OK] Backend ready at http://localhost:{API_PORT}")

    # 5. Start static frontend server
    print(f"\n[ui] Starting frontend on :{UI_PORT}...")
    frontend_dir = os.path.join(ROOT, "frontend")
    ui_proc = subprocess.Popen(
        [PYTHON, "-m", "http.server", str(UI_PORT),
         "--bind", "0.0.0.0",
         "--directory", frontend_dir],
        cwd=ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    processes.append(ui_proc)
    _stream(ui_proc, "ui")
    time.sleep(1)   # tiny grace period for the static server

    # 6. Done
    print()
    print("=" * 50)
    print(f"  [OK] LEVI is running!")
    print(f"  Open -> http://localhost:{UI_PORT}")
    print(f"  API  -> http://localhost:{API_PORT}/docs")
    print("  Press Ctrl+C to stop")
    print("=" * 50)

    # 7. Monitor — restart crashed processes
    while True:
        time.sleep(5)
        if api_proc.poll() is not None:
            print("[api] Process died - restarting...")
            api_proc = subprocess.Popen(
                [PYTHON, "-m", "uvicorn", "backend.main:app",
                 "--host", "0.0.0.0", "--port", str(API_PORT),
                 "--reload", "--reload-dir", backend_dir],
                cwd=ROOT, env=env,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            )
            processes[0] = api_proc
            _stream(api_proc, "api")
        if ui_proc.poll() is not None:
            print("[ui] Process died - restarting...")
            ui_proc = subprocess.Popen(
                [PYTHON, "-m", "http.server", str(UI_PORT),
                 "--bind", "0.0.0.0", "--directory", frontend_dir],
                cwd=ROOT, env=env,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            )
            processes[1] = ui_proc
            _stream(ui_proc, "ui")

if __name__ == "__main__":
    main()