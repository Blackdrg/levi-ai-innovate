import httpx
import json
import asyncio

async def check_ollama():
    url = "http://localhost:11434/api/tags"
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(url)
            if resp.status_code == 200:
                models = resp.json().get("models", [])
                print(f"Ollama Version: {resp.headers.get('warning', 'Unknown')}")
                print("Available Models:")
                for m in models:
                    print(f" - {m['name']}: {m['size'] / 1024**3:.2f} GB")
                
                # Check for 8B models
                has_8b = any("8b" in m["name"].lower() for m in models)
                print(f"\nHas 8B model: {has_8b}")
            else:
                print(f"Error: {resp.status_code}")
        except Exception as e:
            print(f"Error connecting to Ollama: {e}")

if __name__ == "__main__":
    asyncio.run(check_ollama())
