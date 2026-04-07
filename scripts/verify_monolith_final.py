"""
Sovereign OS Graduation Audit v14.0.0.
The final technical verification of LEVI-AI's autonomous cognitive OS.
"""

import os
import asyncio
import logging
from datetime import datetime
from backend.engines.chat.handoff import SovereignHandoff
from backend.core.v8.rules_engine import RulesEngine
from backend.core.v8.learning import PatternRegistry
from backend.core.evolution_tasks import _execute_evolution_logic
from backend.db.firestore_db import db as firestore_db

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger("graduation_audit")

async def audit_local_sovereignty():
    """Verifies v10.0 Offline Mode failover."""
    logger.info("[Audit] Testing LOCAL SOVEREIGNTY (v10.0)...")
    os.environ["OFFLINE_MODE"] = "true"
    
    analysis = SovereignHandoff.analyze_mission("Complex research into ancient Greek philosophy.")
    provider = SovereignHandoff.select_provider(analysis)
    
    if provider == "local":
        logger.info("[Audit] [PASS] Offline Mode correctly forced LOCAL inference.")
        return True
    else:
        logger.error(f"[Audit] [FAIL] Offline Mode leaked to {provider}.")
        return False

async def audit_autonomous_evolution():
    """Verifies v11.0 Rule Promotion logic."""
    logger.info("[Audit] Testing AUTONOMOUS EVOLUTION (v11.0)...")
    
    # Simulate a recurring high-fidelity pattern
    query = "What is the meaning of life?"
    response = "To find resonance with the universe."
    
    # 3-turn pattern clustering simulation
    PatternRegistry.track_pattern("system", query, response)
    PatternRegistry.track_pattern("system", query, response)
    promoted = PatternRegistry.track_pattern("system", query, response)
    
    if promoted:
        rules_engine = RulesEngine()
        rules_engine.create_rule(query, response)
        
        rule_check = await rules_engine.get_rule(query)
        if rule_check == response:
            logger.info("[Audit] [PASS] High-fidelity pattern promoted to Rules Engine.")
            return True
            
    logger.error("[Audit] [FAIL] Rule promotion cycle failed.")
    return False

async def audit_recursive_patching():
    """Verifies v11.0 Recursive Self-Correction."""
    logger.info("[Audit] Testing RECURSIVE PATCHING (v11.0)...")
    
    # This triggers the evolution logic which includes patch simulation
    await _execute_evolution_logic()
    
    # Check if any patches were registered in the system_patches collection
    patches = await asyncio.to_thread(
        lambda: firestore_db.collection("system_patches").limit(1).get()
    )
    
    if len(patches) > 0:
        logger.info("[Audit] [PASS] Recursive System Patch successfully registered.")
        return True
    
    logger.error("[Audit] [FAIL] No patches generated for recurring failures.")
    return False

async def run_graduation_audit():
    """Executes the final Sovereign Audit."""
    print("=" * 60)
    print(f"LEVI-AI SOVEREIGN GRADUATION AUDIT v14.0.0 - {datetime.now().strftime('%Y-%m-%d')}")
    print("=" * 60)
    
    results = [
        ("V10.0 LOCAL SOVEREIGNTY", await audit_local_sovereignty()),
        ("V11.0 RULE PROMOTION   ", await audit_autonomous_evolution()),
        ("V11.0 RECURSIVE PATCHING", await audit_recursive_patching())
    ]
    
    all_passed = all(r[1] for r in results)
    
    print("-" * 60)
    for name, passed in results:
        status = " [OK] " if passed else "[FAIL]"
        print(f"{name:25} {status}")
    print("-" * 60)
    
    if all_passed:
        print("GRADUATION STATUS: SOVEREIGN ALIGNED (100% READINESS)")
        print("THE SOVEREIGN OS GRADUATION IS COMPLETE.")
    else:
        print("GRADUATION STATUS: SYSTEM DRIFT DETECTED - AUDIT FAILED")
    print("=" * 60)
    
    return all_passed

if __name__ == "__main__":
    asyncio.run(run_graduation_audit())
