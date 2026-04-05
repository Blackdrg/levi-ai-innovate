import asyncio
import os
import json
from backend.services.knowledge_extractor import KnowledgeExtractor
from backend.memory.graph_engine import GraphEngine
from backend.core.v8.learning import LearningLoopV13
from dotenv import load_dotenv

load_dotenv()

async def verify_knowledge_layer():
    print("--- 🧠 v13 Knowledge Layer Verification ---")
    
    # 1. Test Extraction (Ollama)
    extractor = KnowledgeExtractor()
    user_input = "Alice works as a Senior Engineer at NASA and loves Python."
    bot_response = "That's impressive! NASA definitely values Python for its data analysis and mission control systems."
    
    print("\n[1/3] Testing Knowledge Extraction (Ollama)...")
    triplets = await extractor.distill_triplets(user_input, bot_response)
    
    if triplets:
        print(f"✅ Extracted {len(triplets)} triplets:")
        for t in triplets:
            print(f"   ({t.subject.name})-[{t.predicate.type.value}]->({t.object.name}) | Type: {t.subject.type.value}")
    else:
        print("❌ Extraction failed or returned no triplets.")
        return

    # 2. Test Storage (Neo4j)
    print("\n[2/3] Testing Graph Storage (Neo4j)...")
    graph = GraphEngine()
    for t in triplets:
        await graph.store.upsert_triplet(t)
    print("✅ Triplets merged into Sovereign Knowledge Graph.")

    # 3. Test Resonance (Retrieval)
    print("\n[3/3] Testing Context Resonance (2-Hop)...")
    resonance = await graph.get_connected_resonance("default_user", "What do we know about Alice?")
    
    if resonance:
        print(f"✅ Retrieved {len(resonance)} resonance facts:")
        for r in resonance:
            print(f"   - {r['fact']}")
    else:
        print("❌ Resonance retrieval failed.")
    
    await graph.close()
    print("\n--- ✅ VERIFICATION COMPLETE ---")

if __name__ == "__main__":
    asyncio.run(verify_knowledge_layer())
