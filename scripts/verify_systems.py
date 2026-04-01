import os
import sys
import asyncio
import uuid
import tempfile

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# 1. Test Streaming alone
async def test_streaming_alone():
    print("\n--- 1. Testing Streaming Alone ---")
    try:
        from backend.services.orchestrator.brain import LeviBrain
        from backend.services.orchestrator.planner import IntentResult
        brain = LeviBrain()
        
        # Test stream pipeline directly
        intent = IntentResult(intent_type="chat", complexity_level=1, confidence_score=0.9, estimated_cost_weight="low", parameters={})
        context = {
            "user_tier": "free",
            "mood": "philosophical",
            "history": [],
            "user_id": "test_user"
        }
        
        stream_res = await brain._stream_pipeline("Hello LEVI. This is a streaming test.", intent, context, "req_123")
        
        print(f"Route Selected: {stream_res['route']}")
        print("Generated Stream chunks:")
        
        count = 0
        async for chunk in stream_res['stream']:
            print(f"Chunk {count}: {chunk.strip()[:50]}...")
            count += 1
            if count > 3: # Just test the first few for validation
                print("... stream functional.")
                break
        print("✅ Streaming Alone: PASS")
    except Exception as e:
        print(f"❌ Streaming Alone: FAIL ({e})")

# 2. Test FAISS retrieval
async def test_faiss_retrieval():
    print("\n--- 2. Testing FAISS Document Engine ---")
    try:
        from backend.services.documents.service import DocumentService
        import PyPDF2
        
        # Create a dummy txt file
        fd, path = tempfile.mkstemp(suffix=".txt")
        with os.fdopen(fd, 'w') as f:
            f.write("The quick brown fox jumps over the lazy LEVI AI system. LEVI AI uses Euclidean L2 FAISS indices for extreme accuracy.")
            
        user_id = f"test_{uuid.uuid4().hex[:8]}"
        
        print(f"Processing dummy document...")
        res = await DocumentService.process_file(path, user_id, "dummy.txt")
        print(res)
        
        print(f"Querying FAISS for context...")
        context = await DocumentService.query_documents(user_id, "What does LEVI AI use?")
        
        if "Euclidean L2 FAISS" in context:
            print("✅ FAISS Retrieval: PASS")
            print(f"Context retrieved: {context[:100]}...")
        else:
            print("❌ FAISS Retrieval: FAIL (Context not found)")
            
        # Cleanup
        os.remove(path)
    except Exception as e:
        print(f"❌ FAISS Retrieval: FAIL ({e})")

# 3. Test Memory Recall
async def test_memory_recall():
    print("\n--- 3. Testing Memory Recall & Trimming ---")
    try:
        from backend.services.orchestrator.memory_manager import MemoryManager
        
        user_id = f"mem_user_{uuid.uuid4().hex[:8]}"
        session_id = f"sess_{uuid.uuid4().hex[:8]}"
        
        print("Storing 25 messages to trigger 20-message trim...")
        for i in range(25):
            await MemoryManager.store_memory(user_id, session_id, f"User MSG {i}", f"Bot MSG {i}")
            
        short_term = await MemoryManager.get_short_term_memory(session_id)
        
        if len(short_term) <= 20:
             print(f"✅ Memory Trimming Limit Enforced: {len(short_term)} messages")
        else:
             print(f"❌ Memory Trimming Failed: {len(short_term)} messages")
             
        # Combined context test
        context = await MemoryManager.get_combined_context(user_id, session_id, "Hello")
        if "history" in context and "long_term" in context:
            print("✅ Combined Context Stitching: PASS")
        else:
            print("❌ Combined Context Stitching: FAIL")
    except Exception as e:
         print(f"❌ Memory Recall: FAIL ({e})")

# 4. Test Brain Routing
async def test_brain_routing():
    print("\n--- 4. Testing Brain Orchestration Routing ---")
    try:
        from backend.services.orchestrator.planner import detect_orchestration_route, check_rules
        
        queries = [
            ("search the latest weather updates in tokyo", "search"),
            ("i uploaded a pdf document, can you summarize it according to the file", "document"),
            ("hello, how are you", "chat"),
            ("who are you?", "chat")
        ]
        
        all_pass = True
        for query, expected in queries:
            route_res = detect_orchestration_route(query)
            if route_res["route"] != expected:
                all_pass = False
                print(f"❌ Route '{query}' -> Expected {expected}, got {route_res['route']}")
            else:
                print(f"✅ Route '{query}' -> {route_res['route']} (Conf: {route_res['confidence']:.2f})")
                
        if all_pass:
             print("✅ Brain Routing Protocol: PASS")
    except Exception as e:
        print(f"❌ Brain Routing Protocol: FAIL ({e})")

async def main():
    print("🚀 Initiating LEVI-AI v6.8 Validation Sequence...")
    await test_streaming_alone()
    await test_faiss_retrieval()
    await test_memory_recall()
    await test_brain_routing()
    print("\n🏁 Validation Sequence Complete.")

if __name__ == "__main__":
    asyncio.run(main())
