import requests
import json
import base64

BASE_URL = "http://127.0.0.1:8000"

def test_chat():
    print("Testing Chat...")
    resp = requests.post(f"{BASE_URL}/chat", json={"session_id": "test", "message": "hello"})
    print(f"Status: {resp.status_code}")
    print(f"Response: {resp.json()}")

def test_generate_image():
    print("\nTesting Generate Image with Context...")
    test_cases = [
        {"text": "The stars are the street lights of eternity", "author": "Unknown", "mood": "philosophical"},
        {"text": "Nature always wears the colors of the spirit", "author": "Emerson", "mood": "calm"},
        {"text": "The only way to predict the future is to create it", "author": "Peter Drucker", "mood": "futuristic"}
    ]
    
    for i, case in enumerate(test_cases):
        print(f"Case {i+1}: {case['text']}")
        resp = requests.post(f"{BASE_URL}/generate_image", json=case)
        print(f"Status: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            print(f"Image base64 length: {len(data['image_b64'])}")
            img_data = base64.b64decode(data['image_b64'].split(',')[1])
            filename = f"test_gen_image_{i+1}.png"
            with open(filename, "wb") as f:
                f.write(img_data)
            print(f"Image saved to {filename}")
        else:
            print(f"Error: {resp.text}")

def test_hindi_generation():
    print("\nTesting Hindi Generation...")
    resp = requests.post(f"{BASE_URL}/chat", json={
        "session_id": "test_hi", 
        "message": "मुझे सफलता पर एक विचार बताओ", 
        "lang": "hi"
    })
    print(f"Status: {resp.status_code}")
    if resp.status_code == 200:
        print(f"Response: {resp.json()}")
    else:
        print(f"Error: {resp.text}")

if __name__ == "__main__":
    test_chat()
    test_generate_image()
    test_hindi_generation()
