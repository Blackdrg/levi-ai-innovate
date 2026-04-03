import asyncio
import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), "backend"))

async def test_integration():
    print("--- Testing LeviBrain v8 Integration ---")
    
    from backend.api.orchestrator import handle_chat, stream_chat
    
    user_id = "test_user_v8"
    message = "Hello Levi, are you upgraded to v8?"
    
    print(f"\n1. Testing handle_chat...")
    try:
        response = await handle_chat(message, user_id)
        print(f"Response received: {response.get('response', '')[:100]}...")
        print("✅ handle_chat integration successful.")
    except Exception as e:
        print(f"❌ handle_chat failed: {e}")

    print(f"\n2. Testing stream_chat...")
    try:
        count = 0
        async for chunk in stream_chat(message, user_id):
            print(f"Chunk {count}: {chunk}")
            count += 1
            if count > 5: break # Just test first few chunks
        print("✅ stream_chat integration successful.")
    except Exception as e:
        print(f"❌ stream_chat failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_integration())
