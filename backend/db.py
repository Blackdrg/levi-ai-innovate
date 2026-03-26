# DEPRECATED: Legacy SQL Database Configuration
# This application is now Firestore-native.
# This file is kept only to prevent import errors during transition.

def get_db():
    """Mock get_db for legacy components."""
    yield None

class Base:
    """Mock Base for legacy components."""
    pass

DATABASE_URL = "firestore://native"
engine = None
SessionLocal = None
