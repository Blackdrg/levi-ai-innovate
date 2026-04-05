import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()

OLLAMA_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

def test_ollama_connection():
    print(f"--- Testing Connection to Ollama at {OLLAMA_URL} ---")
    try:
        response = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        if response.status_code == 200:
            models = response.json().get("models", [])
            print(f"✅ Connection successful!")
            print(f"Available Models: {[m['name'] for m in models]}")
            return True
        else:
            print(f"❌ Connection failed with status code {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error connecting to Ollama: {str(e)}")
        return False

def test_inference():
    print(f"\n--- Testing Inference with llama3 ---")
    payload = {
        "model": "llama3",
        "prompt": "Say 'Local Brain Active' if you can hear me.",
        "stream": False
    }
    try:
        response = requests.post(f"{OLLAMA_URL}/api/generate", json=payload, timeout=30)
        if response.status_code == 200:
            result = response.json().get("response", "")
            print(f"✅ Local Brain Response: {result}")
            return True
        else:
            print(f"❌ Inference failed with status code {response.status_code}")
            print(f"Error: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error during inference: {str(e)}")
        return False

if __name__ == "__main__":
    if test_ollama_connection():
        test_inference()
