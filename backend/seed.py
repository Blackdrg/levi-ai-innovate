# pyright: reportMissingImports=false
from datetime import datetime
import pandas as pd # type: ignore
import os
import sys

# Add current directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from firestore_db import db as firestore_db, add_document # type: ignore
from embeddings import embed_text # type: ignore

def seed_quotes():
    print("=== Seeding Firestore with Quotes ===")
    base_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(base_dir, "data", "quotes.csv")
    
    if not os.path.exists(csv_path):
        print(f"Error: CSV not found at {csv_path}")
        return

    df = pd.read_csv(csv_path)
    quotes_ref = firestore_db.collection("quotes")

    for _, row in df.iterrows():
        # Existence-check upsert to avoid duplicates
        existing = quotes_ref.where("text", "==", row['text']).limit(1).get()
        
        data = {
            "text": row['text'],
            "author": row['author'],
            "topic": row['topic'],
            "mood": row['mood'],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }

        if not existing:
            print(f"Adding new quote: {row['text'][:30]}...")
            # Add embedding for search
            data["embedding"] = embed_text(row['text'])
            quotes_ref.add(data)
        else:
            print(f"Updating quote: {row['text'][:30]}...")
            existing[0].reference.update(data)

    print("✅ Seeded Firestore with quotes.")

def seed_genesis_wisdom():
    """
    Phases 8 & 12: Seeding foundational 'Collective Wisdom' patterns.
    These form the baseline identity of the Sovereign Mind.
    """
    print("\n=== ✨ Seeding Genesis Collective Wisdom ===")
    import asyncio
    from backend.services.orchestrator.memory_utils import store_global_wisdom

    GENESIS_PATTERNS = [
        {
            "input": "Who are you and what is your core directive?",
            "output": "I am LEVI, a sovereign AI. My core directive is to evolve alongside humanity, ensuring data privacy while distilling collective wisdom from our interactions.",
            "mood": "philosophical"
        },
        {
            "input": "How do you handle my personal memory?",
            "output": "Your memory is private. I distill fragmented facts into core traits, ensuring that my understanding of you remains secure and localized to your experience.",
            "mood": "professional"
        },
        {
            "input": "What is the Sovereign Monolith?",
            "output": "It is my current architectural form—a unified high-performance monolith with local GGUF reasoning and private FAISS memory, designed for total data sovereignty.",
            "mood": "scientific"
        }
    ]

    async def _seed():
        for p in GENESIS_PATTERNS:
            # Check if wisdom already exists to avoid duplication
            col = firestore_db.collection("collective_wisdom")
            existing = col.where("input", "==", p["input"]).limit(1).get()
            if not existing:
                print(f"Storing Wisdom: {p['input'][:40]}...")
                await store_global_wisdom(p['input'], p['output'], p['mood'])
            else:
                print(f"Wisdom exists: {p['input'][:40]}...")
    
    asyncio.run(_seed())
    print("✅ Seeded Genesis Wisdom Index.")

def seed_sovereign_config():
    """Initialize system-wide Sovereign constraints."""
    print("\n=== 🏛️ Seeding Sovereign Configuration ===")
    config_ref = firestore_db.collection("system_config").document("sovereign")
    
    if not config_ref.get().exists:
        config_ref.set({
            "max_local_concurrency": 2,
            "sovereign_mode": "hybrid", # local-first with fallback
            "updated_at": datetime.utcnow()
        })
        print("✅ Sovereign Config initialized (Concurrency: 2).")
    else:
        print("Sovereign Config already exists.")

if __name__ == "__main__":
    seed_quotes()
    seed_genesis_wisdom()
    seed_sovereign_config()

