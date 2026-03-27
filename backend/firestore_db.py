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
            # Try default initialization first (works on GCP or with GOOGLE_APPLICATION_CREDENTIALS)
            cred = credentials.ApplicationDefault()
            firebase_admin.initialize_app(cred)
            print("[Firebase] Initialization successful (Default)")
    except Exception as e:
        raise RuntimeError(f"Firebase init failed: {e}")

if firebase_admin._apps and not db:
    try:
        db = firestore.client()
    except Exception as e:
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

def add_document(collection_name: str, data: dict):
    try:
        data['created_at'] = datetime.utcnow()
        update_time, doc_ref = db.collection(collection_name).add(data, timeout=10)
        return doc_ref.id
    except Exception as e:
        print(f"⚠️ Firestore Add Error: {e}")
        return None

def update_document(collection_name: str, document_id: str, data: dict):
    try:
        doc_ref = db.collection(collection_name).document(document_id)
        doc_ref.update(data, timeout=10)
        return True
    except Exception as e:
        print(f"⚠️ Firestore Update Error: {e}")
        return False

def delete_document(collection_name: str, document_id: str):
    try:
        db.collection(collection_name).document(document_id).delete(timeout=10)
        return True
    except Exception as e:
        print(f"⚠️ Firestore Delete Error: {e}")
        return False

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
