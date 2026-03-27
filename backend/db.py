# DEPRECATED: Legacy SQL Database Configuration
# This application is now Firestore-native.
# This file is kept only to prevent import errors during transition.

def get_db():
    """Mock get_db for legacy components."""
    yield None

from sqlalchemy import MetaData
from sqlalchemy.ext.declarative import declarative_base

# Create a proper Base for Alembic to detect
Base = declarative_base()
Base.metadata = MetaData()

DATABASE_URL = "firestore://native"
engine = None
SessionLocal = None
