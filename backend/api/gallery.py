"""
backend/api/gallery.py

Gallery and Feed API - Handles public and private content exploration.
Refactored from backend/services/gallery/router.py.
"""

import logging
import hashlib
import json
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from backend.utils.exceptions import LEVIException
from backend.auth import get_current_user, get_current_user_optional
from backend.firestore_db import db as firestore_db
from backend.models import Query
from backend.redis_client import get_cached_search, cache_search, HAS_REDIS
from google.cloud import firestore as google_firestore
from backend.generation import fetch_open_source_quote, generate_quote
from backend.utils.robustness import standard_retry

logger = logging.getLogger(__name__)
router = APIRouter(prefix="", tags=["Gallery"])

@router.get("/daily_quote")
async def get_daily_quote(response: Response, mood: str = "philosophical"):
    """
    Returns a curated or generated daily quote.
    """
    response.headers["Cache-Control"] = "public, max-age=3600, stale-while-revalidate=86400"
    try:
        quotes_ref = firestore_db.collection("quotes")
        docs = list(quotes_ref.limit(10).stream())
        if docs:
            import random
            doc = random.choice(docs)
            return doc.to_dict()
        
        quote_text = generate_quote("existence", mood=mood)
        return {"text": quote_text, "author": "LEVI", "mood": mood}
    except Exception as e:
        logger.error(f"Daily quote failure: {e}")
        return {"text": "Silence is the sleep that nourishes wisdom.", "author": "Bacon", "mood": "zen"}

@router.get("/feed", response_model=List[dict])
async def get_feed(request: Request, response: Response, limit: int = 20, offset: int = 0):
    """
    Returns the global content feed.
    """
    response.headers["Cache-Control"] = "public, max-age=60, stale-while-revalidate=600"
    try:
        feed_ref = firestore_db.collection("feed_items")
        query = feed_ref.order_by("timestamp", direction=google_firestore.Query.DESCENDING).limit(limit).offset(offset)
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
        
        # ETag calculation for browser caching
        res_json = json.dumps(results, sort_keys=True)
        etag = f'W/"{hashlib.md5(res_json.encode()).hexdigest()}"'
        
        if request.headers.get("If-None-Match") == etag:
            return Response(status_code=304)
            
        response.headers["ETag"] = etag
        return results
    except Exception:
        return []

@router.post("/like/{item_type}/{item_id}")
async def like_item(item_type: str, item_id: str):
    """
    Increments the like count for a specific item.
    """
    try:
        collection = "quotes" if item_type == "quote" else "feed_items"
        if item_type not in ("quote", "feed"):
            raise LEVIException("Invalid item category.", status_code=400)

        item_ref = firestore_db.collection(collection).document(item_id)
        if not item_ref.get().exists:
            raise LEVIException("Item lost in the void.", status_code=404)

        item_ref.update({"likes": google_firestore.Increment(1)})
        
        from backend.firestore_db import update_analytics
        update_analytics("likes_count")

        return {"status": "success", "message": "Resonance increased."}
    except LEVIException:
        raise
    except Exception as e:
        logger.error(f"Like action failure: {e}")
        raise LEVIException("Action failed.", status_code=500)

@router.get("/me")
@router.get("/my_gallery")
async def get_my_gallery(
    current_user: dict = Depends(get_current_user),
    limit: int = 20,
    offset: int = 0
):
    """
    Returns the current user's personal gallery items.
    """
    uid = current_user.get("uid")
    try:
        feed_ref = firestore_db.collection("feed_items")
        query = (feed_ref
            .where("user_id", "==", uid)
            .order_by("timestamp", direction=google_firestore.Query.DESCENDING)
            .limit(limit).offset(offset))
        docs = query.get()
        return [{
            "id": doc.id,
            "text": doc.to_dict().get("text"),
            "author": doc.to_dict().get("author"),
            "mood": doc.to_dict().get("mood"),
            "image": doc.to_dict().get("image_url") or doc.to_dict().get("image_b64"),
            "video": doc.to_dict().get("video_url"),
            "likes": doc.to_dict().get("likes", 0),
            "time": doc.to_dict().get("timestamp").isoformat() if doc.to_dict().get("timestamp") else None
        } for doc in docs]
    except Exception as e:
        logger.error(f"Gallery retrieval failure: {e}")
        return []

@router.post("/search")
@router.post("/search_quotes", response_model=List[dict])
async def search_quotes(request: Request, query: Query):
    """
    Search for quotes using semantic or text-based matching.
    """
    query_hash = hashlib.md5(f"{query.text}:{query.mood}:{query.topic}".encode()).hexdigest()
    if HAS_REDIS:
        cached = get_cached_search(query_hash)
        if cached:
            return cached

    quotes_ref = firestore_db.collection("quotes")
    
    try:
        from backend.embeddings import embed_text, cosine_sim, HAS_MODEL
        import numpy as np
        
        if HAS_MODEL and query.text:
            query_embedding = embed_text(query.text)
            docs = quotes_ref.limit(100).get()
            
            q_emb = np.array(query_embedding)
            scored = []
            for d in docs:
                data = d.to_dict()
                emb = data.get("embedding")
                if emb:
                    score = cosine_sim(q_emb, np.array(emb))
                    scored.append((data, score))
            
            scored.sort(key=lambda x: x[1], reverse=True)
            results = [s[0] for s in scored[:query.top_k]]
        else:
            docs = list(quotes_ref.limit(query.top_k).stream())
            results = [d.to_dict() for d in docs]
    except Exception:
        docs = list(quotes_ref.limit(query.top_k).stream())
        results = [d.to_dict() for d in docs]

    formatted = [
        {"quote": q.get("text"), "author": q.get("author"),
         "topic": q.get("topic"), "mood": q.get("mood")}
        for q in results
    ]

    if HAS_REDIS:
        cache_search(query_hash, formatted)
    return formatted
