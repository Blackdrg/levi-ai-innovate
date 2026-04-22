# scripts/smoke_test.py
import httpx
import asyncio
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SmokeTest")

MAINFRAME_URL = "http://localhost:8000"
KERNEL_URL = "http://localhost:8001"

async def test_kernel_health():
    logger.info("🧪 Testing Kernel Service Health...")
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(f"{KERNEL_URL}/status")
            if resp.status_code == 200:
                logger.info(f"✅ Kernel Online: {resp.json()}")
                return True
        except Exception as e:
            logger.error(f"❌ Kernel Offline: {e}")
    return False

async def test_mainframe_mission():
    logger.info("🧪 Testing Mainframe Mission Lifecycle...")
    async with httpx.AsyncClient() as client:
        try:
            # Submit a simple mission
            payload = {"user_input": "Who are you?", "user_id": "test_user_001"}
            resp = await client.post(f"{MAINFRAME_URL}/api/mission", json=payload, timeout=30.0)
            if resp.status_code == 200:
                logger.info(f"✅ Mission Accepted: {resp.json().get('mission_id')}")
                return True
            else:
                logger.error(f"❌ Mission Failed: {resp.status_code} - {resp.text}")
        except Exception as e:
            logger.error(f"❌ Mainframe Offline: {e}")
    return False

async def main():
    logger.info("🏁 Starting Sovereign OS Smoke Test...")
    k_ok = await test_kernel_health()
    m_ok = await test_mainframe_mission()
    
    if k_ok and m_ok:
        logger.info("🎉 ALL SYSTEMS GO. LEVI-AI v22.1 is OPERATIONAL.")
    else:
        logger.error("🛑 Smoke Test FAILED. Check logs for substrate anomalies.")

if __name__ == "__main__":
    asyncio.run(main())
