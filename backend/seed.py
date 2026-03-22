import pandas as pd # type: ignore
from sqlalchemy.orm import Session
from db import SessionLocal, engine
from models import Quote, Base
from embeddings import embed_text
import numpy as np # type: ignore

Base.metadata.create_all(engine)

db = SessionLocal()

import os
base_dir = os.path.dirname(os.path.abspath(__file__))
csv_path = os.path.join(base_dir, "data", "quotes.csv")
df = pd.read_csv(csv_path)

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

