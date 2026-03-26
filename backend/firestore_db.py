# backend/firestore_db.py
import os
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime

# Initialize Firebase Admin if not already initialized
if not firebase_admin._apps:
    try:
        cred = credentials.ApplicationDefault()
        firebase_admin.initialize_app(cred)
        print("✅ Firebase initialized")
    except Exception as e:
        print(f"❌ Firebase init failed: {e}")
        raise e  # MUST crash if fails

db = firestore.client()

def get_firestore_db():
    return db

# Utility functions for common Firestore operations
def get_document(collection_name: str, document_id: str):
    doc_ref = db.collection(collection_name).document(document_id)
    doc = doc_ref.get()
    if doc.exists:
        return doc.to_dict()
    return None

def set_document(collection_name: str, document_id: str, data: dict):
    doc_ref = db.collection(collection_name).document(document_id)
    doc_ref.set(data, merge=True)
    return True

def add_document(collection_name: str, data: dict):
    data['created_at'] = datetime.utcnow()
    update_time, doc_ref = db.collection(collection_name).add(data)
    return doc_ref.id

def update_document(collection_name: str, document_id: str, data: dict):
    doc_ref = db.collection(collection_name).document(document_id)
    doc_ref.update(data)
    return True

def delete_document(collection_name: str, document_id: str):
    db.collection(collection_name).document(document_id).delete()
    return True

def query_documents(collection_name: str, filters: list = None, limit: int = 10, order_by: str = None, descending: bool = False):
    query = db.collection(collection_name)
    if filters:
        for field, op, value in filters:
            query = query.where(field, op, value)
    
    if order_by:
        direction = firestore.Query.DESCENDING if descending else firestore.Query.ASCENDING
        query = query.order_by(order_by, direction=direction)
    
    if limit:
        query = query.limit(limit)
    
    docs = query.stream()
    return [{**doc.to_dict(), "id": doc.id} for doc in docs]
