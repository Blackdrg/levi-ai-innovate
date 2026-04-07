"""
Sovereign Firebase v8.
Central Firestore and Authentication initialization for the Sovereign OS.
"""

import os
import logging
import firebase_admin # type: ignore
from firebase_admin import credentials, firestore, auth # type: ignore

logger = logging.getLogger(__name__)

# --- Initialization ---
db = None
auth_client = None

try:
    if not firebase_admin._apps:
        # Check for service account key in environment or file
        sa_path = os.getenv("FIREBASE_SERVICE_ACCOUNT")
        if sa_path and os.path.exists(sa_path):
            cred = credentials.Certificate(sa_path)
            firebase_admin.initialize_app(cred)
        else:
            firebase_admin.initialize_app()
    
    db = firestore.client()
    auth_client = auth
    logger.info("Sovereign Firebase: Link established.")
except Exception as e:
    logger.error(f"Sovereign Firebase: Link failure: {e}")

# --- Central Interface ---
def get_db():
    return db

def get_auth():
    return auth_client
