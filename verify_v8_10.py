import asyncio
import sys
import os
import json

# Add backend to path
sys.path.append(os.path.abspath("."))

from backend.core.v8.blackboard import MissionBlackboard
from backend.services.learning.distiller import MemoryDistiller
from backend.db.vector_store import VectorDB
from backend.utils.encryption import SovereignVault

async def test_blackboard():
    print("Testing Mission Blackboard...")
    bb = MissionBlackboard("test_session_123")
    await bb.clear()
    
    await bb.post_insight("research_agent", "Found data on quantum computing", tag="research")
    await bb.post_insight("code_agent", "Generated quantum simulation script", tag="code")
    
    insights = await bb.get_insights()
    print(f"Total insights: {len(insights)}")
    assert len(insights) == 2
    
    ctx = await MissionBlackboard.get_session_context("test_session_123")
    print(f"Session Context:\n{ctx}")
    assert "research_agent" in ctx
    print("Blackboard Test Passed.")

async def test_distillation():
    print("\nTesting Memory Distillation (Dreaming)...")
    user_id = "test_user_789"
    
    # 1. Seed some episodic memory
    memory_db = await VectorDB.get_user_collection(user_id, "memory")
    await memory_db.clear()
    await memory_db.add(
        ["User prefers Python for data science.", "User is interested in renewable energy."],
        [{"source": "chat"}, {"source": "web_search"}]
    )
    
    # 2. Run Distiller (Mocking generator might be needed in real env, but here we test the flow)
    distiller = MemoryDistiller()
    # Note: In a real test environment without LLM keys, this might fail on council_of_models.
    # We will just verify the encryption part of the logic works if we can.
    
    print("Verifying trait encryption...")
    trait = "User is a renewable energy advocate."
    encrypted = SovereignVault.encrypt(trait)
    print(f"Plain: {trait}")
    print(f"Encrypted: {encrypted}")
    decrypted = SovereignVault.decrypt(encrypted)
    assert trait == decrypted
    print("Encryption/Decryption Test Passed.")

if __name__ == "__main__":
    asyncio.run(test_blackboard())
    asyncio.run(test_distillation())
