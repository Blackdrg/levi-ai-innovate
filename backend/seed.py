# pyright: reportMissingImports=false
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
            "updated_at": pd.Timestamp.utcnow()
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

if __name__ == "__main__":
    seed_quotes()

