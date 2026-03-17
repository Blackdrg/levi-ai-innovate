import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./levi_v2.db")

if "postgresql" in DATABASE_URL:
    engine = create_engine(DATABASE_URL)
else:
    # SQLite fallback
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Ensure pgvector extension exists only for postgres
if "postgresql" in DATABASE_URL:
    try:
        with engine.connect() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            conn.commit()
    except Exception as e:
        print(f"Failed to create pgvector extension: {e}")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

