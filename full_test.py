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
        
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            print(f"Success! Sample response: {str(response.json())[:100]}...")  # type: ignore
            return True
        else:
            print(f"Failed: {response.text}")
            return False
    except Exception as e:
        print(f"Error: {e}")
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
