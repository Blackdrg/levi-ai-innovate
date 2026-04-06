# scripts/verify_ollama_tiers.py
import os
import asyncio
import httpx
from dotenv import load_dotenv

load_dotenv()

async def test_model(model_name: str, prompt: str = "Say 'LEVI Online'"):
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    print(f"Testing {model_name}...")
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{base_url}/api/chat",
                json={
                    "model": model_name,
                    "messages": [{"role": "user", "content": prompt}],
                    "stream": False
                }
            )
            if response.status_code == 200:
                print(f"✅ {model_name} is functional.")
                print(f"Response: {response.json()['message']['content']}")
            else:
                print(f"❌ {model_name} failed with status {response.status_code}.")
    except Exception as e:
        import traceback
        print(f"❌ {model_name} error: {e}")
        traceback.print_exc()

async def test_embedding():
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    model = os.getenv("OLLAMA_MODEL_EMBED", "nomic-embed-text")
    print(f"\nTesting Embedding: {model}...")
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{base_url}/api/embeddings",
                json={
                    "model": model,
                    "prompt": "Sovereign AI"
                }
            )
            if response.status_code == 200:
                dim = len(response.json()["embedding"])
                print(f"✅ {model} is functional. Dimension: {dim}")
                if dim == 768:
                    print("✅ Dimension matches nomic-embed-text standard (768).")
                else:
                    print(f"⚠️ Unexpected dimension: {dim}")
            else:
                print(f"❌ {model} failed with status {response.status_code}.")
                print(f"Response Body: {response.text}")
    except Exception as e:
        print(f"❌ {model} error: {e}")

async def main():
    models = [
        os.getenv("OLLAMA_MODEL_FAST", "phi3:mini"),
        os.getenv("OLLAMA_MODEL_GENERAL", "llama3.1:8b"),
        os.getenv("OLLAMA_MODEL_COMPLEX", "llama3.3:70b")
    ]
    for model in models:
        await test_model(model)
        print("-" * 30)
    await test_embedding()

if __name__ == "__main__":
    asyncio.run(main())
