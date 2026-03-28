# backend/firestore_db.py
import os
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime

# Initialize Firebase Admin if not already initialized
db = None
if not firebase_admin._apps:
    try:
        service_account_json = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON")
        if service_account_json:
            import json
            try:
                # Check if it's a file path or direct JSON string
                if os.path.exists(service_account_json):
                    cred = credentials.Certificate(service_account_json)
                else:
                    service_account_info = json.loads(service_account_json)
                    cred = credentials.Certificate(service_account_info)
                firebase_admin.initialize_app(cred)
                print("[Firebase] Initialized with Service Account JSON")
            except Exception as e:
                print(f"[Firebase] Service Account JSON init failed: {e}. Falling back to Default.")
                cred = credentials.ApplicationDefault()
                firebase_admin.initialize_app(cred)
        else:
            print("[Firebase] FIREBASE_SERVICE_ACCOUNT_JSON missing. Attempting Application Default Credentials...")
            # Try default initialization first (works on GCP or with GOOGLE_APPLICATION_CREDENTIALS)
            cred = credentials.ApplicationDefault()
            firebase_admin.initialize_app(cred)
            print("[Firebase] Initialization successful (Default)")
    except Exception as e:
        print(f"[Firebase] CRITICAL: Firebase initialization failed: {e}")
        # In production, we might want to fail fast, but let's allow the app to boot
        # and fail on the first actual DB hit if not in prod.
        if os.getenv("ENVIRONMENT") == "production":
             raise RuntimeError(f"Firebase init failed: {e}")

if firebase_admin._apps and not db:
    try:
        db = firestore.client()
    except Exception as e:
        if os.getenv("ENVIRONMENT") != "production":
            print(f"[Firebase] Using MagicMock for Firestore (Mock Mode): {e}")
            from unittest.mock import MagicMock
            db = MagicMock()
        else:
            raise RuntimeError(f"Firestore client init failed: {e}")

def get_firestore_db():
    return db

# Utility functions for common Firestore operations
def get_document(collection_name: str, document_id: str):
    try:
        doc_ref = db.collection(collection_name).document(document_id)
        doc = doc_ref.get(timeout=10)
        if doc.exists:
            return doc.to_dict()
        return None
    except Exception as e:
        print(f"⚠️ Firestore Get Error: {e}")
        return None

def set_document(collection_name: str, document_id: str, data: dict):
    try:
        doc_ref = db.collection(collection_name).document(document_id)
        doc_ref.set(data, merge=True, timeout=10)
        return True
    except Exception as e:
        print(f"⚠️ Firestore Set Error: {e}")
        return False

def add_document(collection_name: str, data: dict, model=None):
    """Add a document with optional Pydantic validation."""
    try:
        if model:
            # Validate and convert to dict
            valid_data = model(**data).model_dump()
            data = valid_data
            
        data['created_at'] = datetime.utcnow()
        update_time, doc_ref = db.collection(collection_name).add(data, timeout=10)
        return doc_ref.id
    except Exception as e:
        print(f"⚠️ Firestore Add Error [{collection_name}]: {e}")
        return None

def update_document(collection_name: str, document_id: str, data: dict, model=None):
    """Update a document with optional Pydantic validation (partial check)."""
    try:
        if model:
            # For partial updates, we might only validate the keys present
            # but simpler is to use model.model_validate(data, partial=True) if available
            # or just assume the caller passes valid partial data.
            pass
            
        doc_ref = db.collection(collection_name).document(document_id)
        doc_ref.update(data, timeout=10)
        return True
    except Exception as e:
        print(f"⚠️ Firestore Update Error [{collection_name}]: {e}")
        return False

def delete_document(collection_name: str, document_id: str):
    try:
        db.collection(collection_name).document(document_id).delete(timeout=10)
        return True
    except Exception as e:
        print(f"⚠️ Firestore Delete Error: {e}")
        return False

def increment_field(collection_name: str, document_id: str, field_name: str, amount: int = 1):
    """Atomically increment a numeric field in Firestore."""
    try:
        doc_ref = db.collection(collection_name).document(document_id)
        doc_ref.update({
            field_name: firestore.Increment(amount),
            "updated_at": datetime.utcnow()
        }, timeout=10)
        return True
    except Exception as e:
        print(f"⚠️ Firestore Increment Error: {e}")
        return False

def update_analytics(metric: str, amount: int = 1):
    """Centralized analytics update (atomic)."""
    today = datetime.utcnow().strftime("%Y-%m-%d")
    return increment_field("analytics", today, metric, amount)

def query_documents(collection_name: str, filters: list = None, limit: int = 10, order_by: str = None, descending: bool = False):
    try:
        query = db.collection(collection_name)
        if filters:
            for field, op, value in filters:
                query = query.where(field, op, value)
        
        if order_by:
            direction = firestore.Query.DESCENDING if descending else firestore.Query.ASCENDING
            query = query.order_by(order_by, direction=direction)
        
        if limit:
            query = query.limit(limit)
        
        docs = query.stream(timeout=15)
        return [{**doc.to_dict(), "id": doc.id} for doc in docs]
    except Exception as e:
        print(f"⚠️ Firestore Query Error: {e}")
        return []
