import pandas as pd
from sqlalchemy.orm import Session
try:
    from backend.db import SessionLocal, engine
    from backend.models import Quote, Base
    from backend.embeddings import embed_text
except ImportError:
    from db import SessionLocal, engine
    from models import Quote, Base
    from embeddings import embed_text
import numpy as np
import os

Base.metadata.create_all(engine)
db = SessionLocal()

# Extended Quote Database (Open Source Style)
extended_quotes = [
    # Inspiring
    {"text": "The only way to do great work is to love what you do.", "author": "Steve Jobs", "topic": "Work", "mood": "inspiring"},
    {"text": "Believe you can and you're halfway there.", "author": "Theodore Roosevelt", "topic": "Success", "mood": "inspiring"},
    {"text": "It always seems impossible until it's done.", "author": "Nelson Mandela", "topic": "Perseverance", "mood": "inspiring"},
    
    # Calm / Zen
    {"text": "The soul always knows what to do to heal itself.", "author": "Caroline Myss", "topic": "Healing", "mood": "calm"},
    {"text": "Nature does not hurry, yet everything is accomplished.", "author": "Lao Tzu", "topic": "Nature", "mood": "zen"},
    {"text": "Within you, there is a stillness and a sanctuary.", "author": "Hermann Hesse", "topic": "Inner Peace", "mood": "calm"},
    
    # Energetic
    {"text": "Action is the foundational key to all success.", "author": "Pablo Picasso", "topic": "Action", "mood": "energetic"},
    {"text": "Don't count the days, make the days count.", "author": "Muhammad Ali", "topic": "Motivation", "mood": "energetic"},
    {"text": "The future depends on what you do today.", "author": "Mahatma Gandhi", "topic": "Future", "mood": "energetic"},
    
    # Philosophical / Stoic
    {"text": "We suffer more often in imagination than in reality.", "author": "Seneca", "topic": "Stoicism", "mood": "stoic"},
    {"text": "The unexamined life is not worth living.", "author": "Socrates", "topic": "Philosophy", "mood": "philosophical"},
    {"text": "Happiness is a good flow of life.", "author": "Zeno of Citium", "topic": "Happiness", "mood": "stoic"},
    
    # Cyberpunk / Futuristic
    {"text": "The future is already here – it's just not very evenly distributed.", "author": "William Gibson", "topic": "Technology", "mood": "cyberpunk"},
    {"text": "Technology is a useful servant but a dangerous master.", "author": "Christian Lous Lange", "topic": "Technology", "mood": "futuristic"},
    {"text": "Any sufficiently advanced technology is indistinguishable from magic.", "author": "Arthur C. Clarke", "topic": "Science", "mood": "futuristic"},

    # Melancholic
    {"text": "The heart was made to be broken.", "author": "Oscar Wilde", "topic": "Love", "mood": "melancholic"},
    {"text": "To live is to suffer, to survive is to find some meaning in the suffering.", "author": "Friedrich Nietzsche", "topic": "Life", "mood": "melancholic"},
]

# Load from CSV if exists
if os.path.exists("backend/data/quotes.csv"):
    try:
        df = pd.read_csv("backend/data/quotes.csv")
        for _, row in df.iterrows():
            extended_quotes.append({
                "text": row['text'],
                "author": row['author'],
                "topic": row.get('topic', 'General'),
                "mood": row.get('mood', 'inspiring')
            })
    except:
        pass

print(f"Seeding {len(extended_quotes)} quotes...")

for q_data in extended_quotes:
    emb = embed_text(q_data['text'])
    quote = Quote(
        text=q_data['text'],
        author=q_data['author'],
        topic=q_data['topic'],
        mood=q_data['mood'],
        embedding=emb
    )
    db.merge(quote)

db.commit()
db.close()
print("Seeded DB with extended quotes.")


