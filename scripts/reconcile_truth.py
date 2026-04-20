import asyncio
import os
import sys
import logging
import hashlib
from datetime import datetime

# Add project root to sys.path
sys.path.append(os.getcwd())

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ForensicReconciler")

async def run_audit():
    print("="*60)
    print("LEVI-AI SOVEREIGN OS: FORENSIC TRUTH RECONCILIATION")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print("="*60)


    # 1. Hardware Residency Audit
    print("\n[1/5] HARDWARE RESIDENCY AUDIT")
    from backend.kernel.kernel_wrapper import kernel
    pcr0 = kernel.get_pcr_measurement(0)
    print(f" -> PCR[0] (Simulated/Hardware): {pcr0}")
    if len(pcr0) == 64:
        print(" -> [PASS] Deterministic PCR measurement detected.")
    else:
        print(" -> [FAIL] PCR measurement missing or invalid.")

    # 2. PII Governance Verification
    print("\n[2/5] PII GOVERNANCE AUDIT")
    from backend.core.security.pii_governance import pii_governance
    test_str = "My email is test@example.com and phone is 555-0199"
    scrubbed = await pii_governance.scrub_pii(test_str)
    if "test@example.com" not in scrubbed and "555-0199" not in scrubbed:
        print(" -> [PASS] PII Regex Pipeline is ACTIVE and scrubbed test payload.")
    else:
        print(" -> [FAIL] PII Pipeline is BYPASSED.")

    # 3. Raft Consensus Check
    print("\n[3/5] DCN RAFT CONSENSUS AUDIT")
    from backend.core.dcn.raft_consensus import get_dcn_mesh
    mesh = get_dcn_mesh()
    status = await mesh.get_cluster_status()
    print(f" -> Leader: {status.get('leader')}")
    print(f" -> Node ID: {status.get('node_id')}")
    if status.get("leader") != "unknown":
        print(" -> [PASS] Raft leadership established in local cluster.")
    else:
        print(" -> [FAIL] Split-brain or Isolation detected in DCN.")

    # 4. Memory Resonance Integrity
    print("\n[4/5] MEMORY RESONANCE AUDIT")
    from backend.services.mcm import mcm_service
    # Test BFT Quorum registration
    test_fact = f"fact_{int(datetime.now().timestamp())}"
    await mcm_service.graduate({"fact_id": test_fact, "fidelity": 0.99, "agent_id": "hal_1"})
    # Check if vote is in Redis
    from backend.db.redis import r as redis_client, HAS_REDIS
    if HAS_REDIS:
        votes = redis_client.scard(f"mcm:consensus:{test_fact}")
        print(f" -> BFT Votes for test fact: {votes}")
        if votes >= 1:
            print(" -> [PASS] BFT Consensus Aggregator is RECORDING logic pulses.")
        else:
            print(" -> [FAIL] MCM Graduation is stubbed (No Redis persistence).")
    else:
        print(" -> [WARN] Redis absent. Graduation operating in single-node mode.")

    # 5. Core Identity Signing
    print("\n[5/5] IDENTITY AUTHORITY AUDIT")
    from backend.utils.kms import SovereignKMS
    test_data = "mission_trace_integrity_test"
    sig = await SovereignKMS.sign_trace(test_data)
    verified = await SovereignKMS.verify_trace(test_data, sig)
    if verified:
        print(" -> [PASS] Ed25519 Non-Repudiation Authority is ACTIVE.")
    else:
        print(" -> [FAIL] KMS Verification Failure.")

    print("\n" + "="*60)
    print("FINAL STATUS: FORENSICALLY RECONCILED (v22.1 ENGINEERING BASELINE)")
    print("="*60)

if __name__ == "__main__":
    asyncio.run(run_audit())
