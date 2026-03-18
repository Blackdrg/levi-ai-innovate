import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

# Strict guard for production (Render/Heroku/etc)
IS_PROD = os.getenv("RENDER") == "true" or os.getenv("NODE_ENV") == "production"

# Handle empty or missing DATABASE_URL
if not DATABASE_URL or not DATABASE_URL.strip():
    if IS_PROD:
        raise ValueError("CRITICAL: DATABASE_URL environment variable is NOT set in production!")
    DATABASE_URL = "sqlite:///./levi_v2.db"
else:
    DATABASE_URL = DATABASE_URL.strip()

# Render sometimes gives postgres:// but SQLAlchemy 1.4+ needs postgresql://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Debug logging for URL scheme (safe for logs)
scheme = DATABASE_URL.split("://")[0]
print(f"DATABASE_URL scheme: {scheme}")

if "postgresql" in DATABASE_URL:
    # Production PostgreSQL
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
else:
    # SQLite fallback for local development
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

