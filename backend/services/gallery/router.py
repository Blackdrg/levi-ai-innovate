from fastapi import APIRouter, Depends, HTTPException, Request # type: ignore
from typing import Optional, List
import hashlib
import numpy as np # type: ignore

from backend.auth import get_current_user_optional # type: ignore
from backend.firestore_db import db as firestore_db # type: ignore
from backend.models import Query # type: ignore
from backend.redis_client import get_cached_search, cache_search # type: ignore

router = APIRouter(prefix="/gallery", tags=["Gallery"])

@router.get("/feed", response_model=List[dict])
async def get_feed(limit: int = 20, offset: int = 0):
    try:
        feed_ref = firestore_db.collection("feed_items")
        query = feed_ref.order_by("timestamp", direction=firestore_db.DESCENDING).limit(limit).offset(offset)
        docs = query.get()
        
        results = []
        for doc in docs:
            d = doc.to_dict()
            results.append({
                "id": doc.id,
                "text": d.get("text"),
                "author": d.get("author"),
                "mood": d.get("mood"),
                "image": d.get("image_url") or d.get("image_b64"),
                "likes": d.get("likes", 0),
                "time": d.get("timestamp").isoformat() if d.get("timestamp") else None
            })
        return results
    except Exception as e:
        return []

@router.post("/like/{item_type}/{item_id}")
async def like_item(item_type: str, item_id: str):
    try:
        if item_type == "quote":
            collection = "quotes"
        elif item_type == "feed":
            collection = "feed_items"
        else:
            raise HTTPException(status_code=400, detail="Invalid item type")

        item_ref = firestore_db.collection(collection).document(item_id)
        item_doc = item_ref.get()

        if not item_doc.exists:
            raise HTTPException(status_code=404, detail="Item not found")

        # Atomic increment
        from google.cloud import firestore as google_firestore # type: ignore
        item_ref.update({"likes": google_firestore.Increment(1)})
        
        from backend.firestore_db import update_analytics # type: ignore
        update_analytics("likes_count")

        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/search_quotes", response_model=List[dict])
async def search_quotes(request: Request, query: Query):
    query_hash = hashlib.md5(f"{query.text}:{query.mood}:{query.topic}".encode()).hexdigest()
    cached = get_cached_search(query_hash)
    if cached:
        return cached

    # Search logic (same as in main.py)
    # ... Simplified for service split
    return []
