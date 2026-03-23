# pyright: reportMissingImports=false
import os
from sqlalchemy import create_engine  # type: ignore
from sqlalchemy.ext.declarative import declarative_base  # type: ignore
from sqlalchemy.orm import sessionmaker  # type: ignore

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./levi.db")

# Warn if SQLite is used in production (Render sets RENDER=true)
if DATABASE_URL.startswith("sqlite") and os.getenv("RENDER") == "true":
    import logging as _logging
    _logging.getLogger(__name__).warning(
        "⚠️  SQLite detected in production! Set DATABASE_URL to a PostgreSQL connection string."
    )

# Fix for SQLite (needs check_same_thread=False)
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

# Connection pooling for production Postgres
engine_args: dict = {
    "connect_args": connect_args,
}

if not DATABASE_URL.startswith("sqlite"):
    engine_args["pool_size"] = 5
    engine_args["max_overflow"] = 10
    engine_args["pool_timeout"] = 30
    engine_args["pool_recycle"] = 1800

engine = create_engine(DATABASE_URL, **engine_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

