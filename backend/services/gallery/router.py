from fastapi import APIRouter, Depends, HTTPException, Request, Response # type: ignore
from typing import Optional, List
import hashlib
import numpy as np # type: ignore
import logging

from backend.auth import get_current_user, get_current_user_optional # type: ignore
from backend.firestore_db import db as firestore_db # type: ignore
from backend.models import Query # type: ignore
from backend.redis_client import get_cached_search, cache_search, HAS_REDIS # type: ignore
from google.cloud import firestore as google_firestore # type: ignore
from backend.generation import fetch_open_source_quote, generate_quote # type: ignore

logger = logging.getLogger("gateway.gallery")

router = APIRouter(prefix="/gallery", tags=["Gallery"])

@router.get("/me")
async def get_my_gallery(
    response: Response,
    current_user: dict = Depends(get_current_user)
):
    """Fetch private gallery items. Private caching only."""
    response.headers["Cache-Control"] = "private, max-age=60"
    return {"items": []}

@router.get("/daily_quote")
async def get_daily_quote(response: Response, mood: str = "philosophical"):
    """Phase 42: Optimized daily quote delivery with SWR."""
    response.headers["Cache-Control"] = "public, max-age=3600, stale-while-revalidate=86400"
    try:
        # Try to get from a curated collection first
        quotes_ref = firestore_db.collection("quotes")
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
async def get_feed(request: Request, response: Response, limit: int = 20, offset: int = 0):
    """Phase 42: High-velocity feed with ETag support and SWR."""
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
        
        # ETag Hardening
        import json
        res_json = json.dumps(results, sort_keys=True)
        etag = f'W/"{hashlib.md5(res_json.encode()).hexdigest()}"'
        
        if request.headers.get("If-None-Match") == etag:
            return Response(status_code=304)
            
        response.headers["ETag"] = etag
        return results
    except Exception as e:
        return []

@router.post("/like/{item_type}/{item_id}")
async def like_item(item_type: str, item_id: str, user_id: str = "anonymous"):
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
        item_ref.update({"likes": google_firestore.Increment(1)})
        
        from backend.firestore_db import update_analytics # type: ignore
        update_analytics("likes_count")

        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/my_gallery")
async def get_my_gallery(
    current_user: dict = Depends(get_current_user),
    limit: int = 20,
    offset: int = 0
):
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
        logger.error(f"Gallery error: {e}")
        return []

@router.post("/search_quotes", response_model=List[dict])
async def search_quotes(request: Request, query: Query):
    """
    Search for quotes using advanced vector similarity matching.
    (Synchronized from hardened monolithic implementation)
    """
    query_hash = hashlib.md5(f"{query.text}:{query.mood}:{query.topic}".encode()).hexdigest()
    cached = get_cached_search(query_hash)
    if cached:
        return cached

    quotes_ref = firestore_db.collection("quotes")
    
    if not query.text or not HAS_REDIS:
        docs = list(quotes_ref.limit(query.top_k).stream())
        results = [d.to_dict() for d in docs]
    else:
        try:
            from backend.embeddings import embed_text, cosine_sim, HAS_MODEL # type: ignore
            if HAS_MODEL:
                query_embedding = embed_text(query.text)
                
                # Fetch recent quotes for comparison (limited for Firestore efficiency)
                docs = quotes_ref.limit(100).get()
                
                q_emb = np.array(query_embedding)
                scored = []
                for d in docs:
                    data = d.to_dict()
                    emb = data.get("embedding")
                    if emb:
                        score = cosine_sim(q_emb, np.array(emb))
                        scored.append((data, score))
                
                # Sort by similarity
                scored.sort(key=lambda x: x[1], reverse=True)
                results = [s[0] for s in scored[:query.top_k]]
            else:
                # Basic keyword fallback
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

    cache_search(query_hash, formatted)
    return formatted
