import pandas as pd
from sqlalchemy.orm import Session
from backend.db import SessionLocal, engine
from backend.models import Quote, Base
from backend.embeddings import embed_text
import numpy as np

Base.metadata.create_all(engine)

db = SessionLocal()

# Load CSV
df = pd.read_csv("backend/data/quotes.csv")

for _, row in df.iterrows():
    # Existence-check upsert to avoid duplicates and redundant embedding calls
    existing = db.query(Quote).filter(Quote.text == row['text']).first()
    if not existing:
        emb = embed_text(row['text'])
        quote = Quote(
            text=row['text'],
            author=row['author'],
            topic=row['topic'],
            mood=row['mood'],
            embedding=emb
        )
        db.add(quote)
    else:
        # Update existing if needed
        existing.author = row['author']
        existing.topic = row['topic']
        existing.mood = row['mood']

db.commit()
db.close()
print("Seeded DB with quotes.")

