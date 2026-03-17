
import requests
import os
import sys
import time

# Configuration
FRONTEND_URL = "http://localhost:8080"
BACKEND_URL = "http://localhost:8000"

def test_step(name, check_fn):
    print(f"\n[STEP] {name}...")
    try:
        result, msg = check_fn()
        if result:
            print(f"✅ PASSED: {msg}")
            return True
        else:
            print(f"❌ FAILED: {msg}")
            return False
    except Exception as e:
        print(f"💥 ERROR: {e}")
        return False

def check_frontend_alive():
    try:
        r = requests.get(FRONTEND_URL, timeout=5)
        return r.status_code == 200, f"Frontend (8080) responded with {r.status_code}"
    except:
        return False, "Frontend (8080) unreachable. Did you run 'python run_app.py'?"

def check_backend_alive():
    try:
        r = requests.get(f"{BACKEND_URL}/health", timeout=5)
        return r.status_code == 200, f"Backend (8000) responded with {r.json()}"
    except:
        return False, "Backend (8000) unreachable. Did you run 'python run_app.py'?"

def check_frontend_backend_bridge():
    # This simulates what the browser's JS would do
    try:
        payload = {"session_id": "integration_test", "message": "hello", "lang": "en"}
        r = requests.post(f"{BACKEND_URL}/chat", json=payload, timeout=10)
        return r.status_code == 200, f"Chat API Bridge functional. Response: {r.json().get('response')[:50]}..."
    except Exception as e:
        return False, f"API Bridge failed: {e}"

def check_static_assets():
    assets = [
        "/js/api.js",
        "/js/ui.js",
        "/css/styles.css",
        "/manifest.json"
    ]
    for asset in assets:
        r = requests.get(f"{FRONTEND_URL}{asset}", timeout=5)
        if r.status_code != 200:
            return False, f"Missing asset: {asset}"
    return True, "All critical JS/CSS/Manifest assets are served correctly."

def check_cors_headers():
    # Simulate a CORS preflight request
    headers = {
        "Origin": FRONTEND_URL,
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "Content-Type"
    }
    try:
        r = requests.options(f"{BACKEND_URL}/chat", headers=headers, timeout=5)
        cors_ok = r.headers.get("Access-Control-Allow-Origin") in [FRONTEND_URL, "*"]
        return cors_ok, f"CORS headers: {r.headers.get('Access-Control-Allow-Origin')}"
    except:
        return False, "CORS preflight failed."

if __name__ == "__main__":
    print("="*40)
    print("LEVI UNIFIED SYSTEM INTEGRATION TEST")
    print("="*40)
    
    steps = [
        ("Frontend Availability", check_frontend_alive),
        ("Backend Core Health", check_backend_alive),
        ("Static Asset Integrity", check_static_assets),
        ("Cross-Origin (CORS) Policy", check_cors_headers),
        ("End-to-End API Bridge", check_frontend_backend_bridge)
    ]
    
    passed = 0
    for name, fn in steps:
        if test_step(name, fn):
            passed += 1
            
    print("\n" + "="*40)
    print(f"FINAL RESULT: {passed}/{len(steps)} STEPS PASSED")
    if passed == len(steps):
        print("🚀 THE SYSTEM IS FULLY CONNECTED AND READY!")
    else:
        print("⚠️ SOME CONNECTIONS ARE BROKEN. SEE LOGS ABOVE.")
    print("="*40)
