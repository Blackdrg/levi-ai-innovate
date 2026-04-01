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

import httpx # type: ignore
import argparse

async def test_local_engine():
    logger.info("Testing Local Sovereign Engine (GGUF)...")
    from backend.services.orchestrator.local_engine import handle_local
    try:
        response = await handle_local("Identify yourself.")
        if "LEVI" in response:
            logger.info("Local GGUF Reasoning: OK")
            return True
        else:
            logger.warning(f"Local GGUF returned unexpected response: {response}")
            return False
    except Exception as e:
        logger.error(f"Local GGUF Test Failed: {e}")
        return False

async def test_faiss_persistence():
    logger.info("Testing FAISS Persistence (GCS FUSE)...")
    from backend.services.orchestrator.memory_utils import store_facts, search_relevant_facts
    user_id = "test_verify_user"
    fact = "User prefers sovereign data isolation."
    try:
        await store_facts(user_id, [{"fact": fact, "category": "preference"}])
        results = await search_relevant_facts(user_id, "data isolation", limit=1)
        if results and results[0]["fact"] == fact:
            logger.info("FAISS GCS FUSE Read/Write: OK")
            return True
        else:
            logger.error("FAISS Retrieval Failed or Mismatched")
            return False
    except Exception as e:
        logger.error(f"FAISS Persistence Test Failed: {e}")
        return False

async def test_sse_pulse_api(base_url: str):
    logger.info(f"Testing SSE Pulse API ({base_url})...")
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            headers = {"X-Admin-Key": os.getenv("ADMIN_KEY", "dev_key")}
            # Mock chat request
            async with client.stream("POST", f"{base_url}/api/chat", json={"message": "ping"}, headers=headers) as response:
                if response.status_code != 200:
                    logger.error(f"SSE API Status: {response.status_code}")
                    return False
                
                # Check for SSE content-type
                if "text/event-stream" not in response.headers.get("content-type", ""):
                    logger.error(f"Invalid Content-Type: {response.headers.get('content-type')}")
                    return False
                
                # Read first chunk for 'activity' pulse
                async for line in response.aiter_lines():
                    if line.startswith("event: activity") or line.startswith("event: choice"):
                        logger.info("SSE Intelligence Pulse: OK")
                        return True
                    break
        return False
    except Exception as e:
        logger.error(f"SSE Pulse Test Failed: {e}")
        return False

async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--prod", action="store_true", help="Test remote production URL")
    args = parser.parse_args()
    
    base_url = "https://levi-monolith-u5v7-production.a.run.app" if args.prod else "http://localhost:8080"
    logger.info(f"--- PRODUCTION HARDENING VERIFICATION (Base: {base_url}) ---")
    
    results = {
        "Redis": await test_redis(),
        "Firestore": await test_firestore(),
        "LLM_API": await test_llm_api(),
        "Local_GGUF": await test_local_engine(),
        "FAISS_FUSE": await test_faiss_persistence(),
        "SSE_Pulse": await test_sse_pulse_api(base_url)
    }
    
    logger.info("\n--- FINAL SOVEREIGNTY SUMMARY ---")
    all_ok = True
    for service, ok in results.items():
        status = "PASSED ✅" if ok else "FAILED ❌"
        logger.info(f"{service:12}: {status}")
        if not ok: all_ok = False
            
    if all_ok:
        logger.info("\n🚀 SYSTEM IS SOVEREIGN, SECURE, AND PRODUCTION READY.")
        sys.exit(0)
    else:
        logger.error("\n💔 SYSTEM NOT READY. CRITICAL FAILURES DETECTED.")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
