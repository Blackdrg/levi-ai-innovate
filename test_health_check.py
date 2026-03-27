import httpx

BASE_URL = "http://localhost:8000"

def test_health():
    print("Testing /health endpoint...")
    try:
        resp = httpx.get(f"{BASE_URL}/health", timeout=10)
        print(f"Status: {resp.status_code}")
        print("Body:")
        print(resp.json())
        if resp.status_code == 200:
            print("Health check passed!")
        else:
            print("Health check reported issues.")
    except Exception as e:
        print(f"Error connecting to backend: {e}")

if __name__ == "__main__":
    test_health()
