import asyncio
import logging
import json
from backend.engines.memory.graph_engine import GraphEngine
from backend.core.memory_utils import extract_memory_graph
from backend.memory.manager import MemoryManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_v8_relational_intelligence():
    print("\n--- INITIATING LEVIBRAIN V8.6 RELATIONAL INTELLIGENCE VERIFICATION ---\n")
    
    user_id = "test_user_v8_6"
    
    # 1. Extraction Test
    print("Testing Triplet Extraction...")
    extraction = await extract_memory_graph(
        "I am working on Project Apollo which uses the Rust programming language.",
        "That sounds like an ambitious project! Rust is a great choice for performance."
    )
    triplets = extraction.get("triplets", [])
    print(f"Extracted Triplets: {triplets}")
    assert len(triplets) > 0, "Failed to extract relational triplets."

    # 2. Graph Storage Test
    print("\nTesting Neo4j Storage...")
    graph = GraphEngine()
    for t in triplets:
        await graph.upsert_triplet(user_id, t["subject"], t["relation"], t["object"])
    
    schema = await graph.get_user_schema(user_id)
    print(f"User Knowledge Schema: {len(schema)} relationships found.")
    assert len(schema) >= len(triplets), "Failed to persist triplets to Neo4j."

    # 3. Relational Resonance Test
    print("\nTesting Graph Resonance Traversals...")
    # Find connectivity for 'Project Apollo'
    resonance = await graph.get_connected_resonance(user_id, "Project Apollo")
    print(f"Resonance Findings: {resonance}")
    assert len(resonance) > 0, "Failed to perform graph traversal for relational resonance."

    print("\n--- V8.6 RELATIONAL INTELLIGENCE VERIFICATION COMPLETE ---")
    await graph.close()

if __name__ == "__main__":
    asyncio.run(test_v8_relational_intelligence())
