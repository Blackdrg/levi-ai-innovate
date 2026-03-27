from fastapi import APIRouter, Depends, HTTPException, Request # type: ignore
from typing import Optional, List
import hashlib
import numpy as np # type: ignore

from backend.auth import get_current_user_optional # type: ignore
from backend.firestore_db import db as firestore_db # type: ignore
from backend.models import Query # type: ignore
from backend.redis_client import get_cached_search, cache_search # type: ignore

from backend.generation import fetch_open_source_quote, generate_quote # type: ignore

router = APIRouter(prefix="/gallery", tags=["Gallery"])

@router.get("/daily_quote")
async def get_daily_quote(mood: str = "philosophical"):
    """Fetch a high-quality quote for the daily dose, with fallback."""
    try:
        # Try to get from a curated collection first
        quotes_ref = firestore_db.collection("quotes")
        # In a real app, we'd use a 'daily' flag or random logic
        docs = quotes_ref.limit(5).get()
        if docs:
            import random
            doc = random.choice(docs)
            return doc.to_dict()
        
        # Fallback to AI generation
        quote_text = generate_quote("existence", mood=mood)
        return {"text": quote_text, "author": "LEVI", "mood": mood}
    except Exception as e:
        # Final fallback
        os_quote = fetch_open_source_quote(mood)
        if os_quote:
            return {"text": os_quote["quote"], "author": os_quote["author"], "mood": mood}
        return {"text": "Silence is the sleep that nourishes wisdom.", "author": "Bacon", "mood": "zen"}

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
    """
    Search for quotes using simple keyword matching across Firestore.
    (Optimized for Firestore-native architecture)
    """
    query_hash = hashlib.md5(f"{query.text}:{query.mood}:{query.topic}".encode()).hexdigest()
    cached = get_cached_search(query_hash)
    if cached:
        return cached

    try:
        quotes_ref = firestore_db.collection("feed_items")
        # Simple Firestore filter (limited by Firestore's indexing capabilities)
        q = quotes_ref.order_by("timestamp", direction=firestore_db.DESCENDING)
        
        if query.topic:
            q = q.where("topic", "==", query.topic)
        
        docs = q.limit(query.top_k).get()
        results = []
        for doc in docs:
            d = doc.to_dict()
            results.append({
                "id": doc.id,
                "text": d.get("text"),
                "author": d.get("author", "Unknown"),
                "image": d.get("image_url") or d.get("image_b64"),
                "likes": d.get("likes", 0)
            })
        
        if results:
            cache_search(query_hash, results)
        return results
    except Exception as e:
        return []
