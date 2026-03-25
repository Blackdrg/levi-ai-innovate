import os
import sys

# Load env safely
from dotenv import load_dotenv
if os.path.exists(".env.local"):
    load_dotenv(".env.local")
elif os.path.exists("../.env.local"):
    load_dotenv("../.env.local")

from db import Base, engine
import models
import training_models

print("Generating database schema directly from SQLAlchemy models...")
Base.metadata.create_all(bind=engine)
print("Schema complete.")
