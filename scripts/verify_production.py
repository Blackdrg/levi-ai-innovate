# scripts/verify_production.py
import os
import sys
import asyncio
import logging
from typing import Dict, Any

# Add workspace to path
sys.path.append(os.getcwd())

from backend.redis_client import r as redis_client, HAS_REDIS
from backend.firestore_db import db as firestore_db
from backend.utils.network import ai_service_breaker

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("VERIFY")

async def test_redis():
    logger.info("Testing Redis connection...")
    if not HAS_REDIS:
        logger.error("Redis is NOT connected!")
        return False
    try:
        redis_client.ping()
        logger.info("Redis Ping: OK")
        return True
    except Exception as e:
        logger.error(f"Redis Ping Failed: {e}")
        return False

async def test_firestore():
    logger.info("Testing Firestore connection...")
    try:
        # Try a simple write/read/delete
        doc_ref = firestore_db.collection("health_checks").document("prod_verify")
        doc_ref.set({"status": "ok", "timestamp": "now"})
        doc = doc_ref.get()
        if doc.exists:
            logger.info("Firestore Read/Write: OK")
            doc_ref.delete()
            return True
        else:
            logger.error("Firestore Read Failed: Document not found")
            return False
    except Exception as e:
        logger.error(f"Firestore Test Failed: {e}")
        return False

async def test_llm_api():
    logger.info("Testing LLM API Connectivity (via CircuitBreaker)...")
    from backend.generation import _async_call_llm_api
    
    try:
        # Lightweight test call
        messages = [{"role": "user", "content": "hello"}]
        # We wrap this in our standard breaker to see if it trips
        response = await ai_service_breaker.async_call(
            _async_call_llm_api, 
            messages=messages, 
            model="llama-3.1-8b-instant",
            provider="groq"
        )
        if response:
            logger.info("LLM API (Groq): OK")
            return True
        else:
            logger.error("LLM API Returned empty response")
            return False
    except Exception as e:
        logger.error(f"LLM API Test Failed: {e}")
        return False

async def main():
    logger.info("--- PRODUCTION HARDENING VERIFICATION ---")
    
    results = {
        "Redis": await test_redis(),
        "Firestore": await test_firestore(),
        "LLM_API": await test_llm_api()
    }
    
    logger.info("--- SUMMARY ---")
    all_ok = True
    for service, ok in results.items():
        status = "PASSED" if ok else "FAILED"
        logger.info(f"{service}: {status}")
        if not ok:
            all_ok = False
            
    if all_ok:
        logger.info("SYSTEM READY FOR PRODUCTION LOAD.")
        sys.exit(0)
    else:
        logger.error("SYSTEM NOT READY. FIX FAILURES ABOVE.")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
