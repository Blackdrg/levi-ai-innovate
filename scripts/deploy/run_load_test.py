import subprocess
import time
import json
import os
import sys
from urllib import request, error

# --- Configuration ---
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")
HEALTH_URL = f"{BASE_URL}/health"
TEST_SCRIPT = "tests/load/missions_k6.js"
REPORT_FOLDER = "k6_reports"
CONCURRENCIES = [10, 50, 100]
DURATION = "1m"

def wait_for_backend(url, max_retries=10, delay=5):
    print(f"🔍 Verifying backend availability at {url}...")
    for i in range(1, max_retries + 1):
        try:
            with request.urlopen(url, timeout=2) as response:
                if response.status == 200:
                    print("✅ Backend is ONLINE. Starting baseline sequence.")
                    return True
        except (error.URLError, error.HTTPError):
            print(f"   [WAIT] Backend not responding yet. Retrying ({i}/{max_retries})...")
            time.sleep(delay)
    return False

def run_k6(vus, duration, export_path):
    print(f"\n🚀 [STEP] Running load test with {vus} VUs for {duration}...")
    cmd = [
        "k6", "run", TEST_SCRIPT,
        "--vus", str(vus),
        "--duration", duration,
        f"--summary-export={export_path}"
    ]
    try:
        subprocess.run(cmd, check=True)
        print(f"✨ Successfully completed {vus} VU test.")
    except subprocess.CalledProcessError as e:
        print(f"⚠️ k6 exited with non-zero status: {e}")
    except FileNotFoundError:
        print("❌ FATAL: 'k6' binary not found. Please install k6 (https://k6.io).")
        sys.exit(1)

def main():
    if not os.path.exists(REPORT_FOLDER):
        os.makedirs(REPORT_FOLDER)

    if not wait_for_backend(HEALTH_URL):
        print(f"❌ FATAL: Backend refused connection at {HEALTH_URL} after retries.")
        print("💡 Hint: Start the server using 'run-dev.bat' or the debugger first.")
        sys.exit(1)

    for vus in CONCURRENCIES:
        export_path = os.path.join(REPORT_FOLDER, f"k6_results_vus_{vus}.json")
        run_k6(vus, DURATION, export_path)

        # Basic metric extraction
        if os.path.exists(export_path):
            with open(export_path, 'r') as f:
                data = json.load(f)
                p95 = data.get("metrics", {}).get("http_req_duration", {}).get("values", {}).get("p(95)")
                if p95:
                    print(f"📊 P95 latency at {vus} VUs: {p95:.2f} ms")

    print("\n✅ [DONE] Baseline metrics generated. Inspect k6_reports for HPA wiring.")

if __name__ == "__main__":
    main()
