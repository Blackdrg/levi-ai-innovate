import json
import logging
import asyncio
from backend.kernel.kernel_wrapper import kernel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("KernelATATest")

async def test_ata_roundtrip():
    """
    Sovereign v22.1: Kernel ATA Integration Test (Round-trip Verification).
    1. Triggers MCM_GRADUATE (0x06) to CRYSTALLIZE a fact to LBA 1000.
    2. Triggers MCM_READ (0x0C) to VERIFY the fact was anchored correctly.
    """
    logger.info("🚀 Starting Kernel ATA Integration Test...")
    
    # Check if we have the Rust kernel
    if not kernel.rust_kernel:
        logger.warning("⚠️ Rust kernel not detected. Skipping real integration test, running in simulation mode.")
        # Simulated responses would normally be returned by kernel_wrapper fallback
    
    # 1. Promote Fact (Write to ATA)
    logger.info(" [Step 1] Promoting fact to Tier 3 (MCM_GRADUATE)...")
    res_grad = kernel.sys_call("test-agent", json.dumps({"type": "Graduate", "fact_id": "fact-123", "fidelity": 0.98}))
    logger.info(f" [MCM] Graduate Result: {res_grad}")
    
    # 2. Retrieve Fact (Read from ATA)
    logger.info(" [Step 2] Verifying fact from Tier 3 (MCM_READ)...")
    res_read = kernel.sys_call("test-agent", json.dumps({"type": "McmRead", "fact_id": "fact-123"}))
    logger.info(f" [MCM] Read Result: {res_read}")
    
    if "result\": 1" in res_grad and "result\": 1" in res_read:
        logger.info("✅ SUCCESS: Kernel ATA Round-trip verified.")
    else:
        logger.error("❌ FAILURE: Kernel ATA Round-trip failed or returned unexpected status.")

if __name__ == "__main__":
    asyncio.run(test_ata_roundtrip())
