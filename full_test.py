# pyright: reportMissingImports=false

import requests  # type: ignore
import json

BASE_URL = "http://localhost:8000"

def test_endpoint(name, method, endpoint, payload=None):
    url = f"{BASE_URL}{endpoint}"
    print(f"\n--- Testing {name} ---")
    try:
        if method == "GET":
            response = requests.get(url, timeout=10)
        else:
            response = requests.post(url, json=payload, timeout=10)
        
        with open("test_results_detailed.txt", "a", encoding="utf-8") as f:
            f.write(f"\n--- Testing {name} ---\n")
            f.write(f"Status: {response.status_code}\n")
            if response.status_code == 200:
                f.write(f"Success! Response: {response.text}\n")
                print(f"Status: {response.status_code} (Success)")
                return True
            else:
                f.write(f"Failed Body: {response.text}\n")
                print(f"Status: {response.status_code} (Failed)")
                return False
    except Exception as e:
        with open("test_results_detailed.txt", "a", encoding="utf-8") as f:
            f.write(f"\n--- Testing {name} ---\nError: {e}\n")
        print(f"Status: Error ({e})")
        return False

if __name__ == "__main__":
    tests = [
        ("Health Check", "GET", "/health"),
        ("Daily Quote", "GET", "/daily_quote"),
        ("Analytics", "GET", "/analytics"),
        ("English Chat", "POST", "/chat", {"session_id": "test", "message": "What is life?", "lang": "en"}),
        ("Hindi Chat", "POST", "/chat", {"session_id": "test", "message": "नमस्ते", "lang": "hi"}),
        ("Quote Generation", "POST", "/generate", {"text": "Success", "mood": "Inspiring"})
    ]
    
    results = []
    for t in tests:
        results.append(test_endpoint(*t))
    
    print("\n" + "="*20)
    print(f"Final Result: {sum(results)}/{len(tests)} passed.")
    print("="*20)
