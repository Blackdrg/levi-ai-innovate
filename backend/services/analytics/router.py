from fastapi import APIRouter, Depends, HTTPException, Request # type: ignore
from typing import Optional
import logging

from backend.auth import verify_admin # type: ignore
from backend.firestore_db import db as firestore_db # type: ignore

router = APIRouter(prefix="/analytics", tags=["Analytics"])

@router.get("")
async def get_analytics_data(request: Request):
    try:
        # Check from analytics collection
        analytics_ref = firestore_db.collection("analytics")
        docs = analytics_ref.stream()
        
        total_chats = 0
        total_likes = 0
        total_users = 0
        
        for doc in docs:
            data = doc.to_dict()
            total_chats += data.get("chats_count", 0)
            total_likes += data.get("likes_count", 0)
            total_users += data.get("daily_users", 0)
            
        return {
            "total_chats": total_chats,
            "daily_users": total_users,
            "popular_topics": ["philosophy", "success", "wisdom"],
            "likes_count": total_likes,
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail="Analytics temporarily unavailable")

@router.get("/admin/health")
async def admin_health_check(is_admin: bool = Depends(verify_admin)):
    return {"status": "ok", "admin": True}

