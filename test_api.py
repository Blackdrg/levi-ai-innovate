
import requests
import json

def test_chat():
    url = "http://127.0.0.1:8000/chat"
    payload = {
        "session_id": "test_session",
        "message": "hi",
        "lang": "en"
    }
    headers = {"Content-Type": "application/json"}
    
    try:
        response = requests.post(url, data=json.dumps(payload), headers=headers, timeout=10)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_chat()
