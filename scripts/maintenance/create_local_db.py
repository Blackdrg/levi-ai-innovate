import os
from dotenv import load_dotenv

load_dotenv(".env.local", override=True)

from backend.db import Base, engine
from backend import models
from backend import training_models

print(f"[Schema] Generating database at: {engine.url}")
Base.metadata.create_all(bind=engine)
print("[Schema] Complete!")
