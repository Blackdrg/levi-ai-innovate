# create_db.py — DEPRECATED (2026-03-28)
# This file is an obsolete legacy SQL creation script.
# The LEVI AI platform has fully migrated to a Firestore-native architecture.
# Use firestore_db.py for all database interactions.
import logging
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    logger.warning("This script is DEPRECATED and does nothing. Use firestore_db.py.")
    print("DEPRECATED: LEVI AI is now Firestore-native.")
