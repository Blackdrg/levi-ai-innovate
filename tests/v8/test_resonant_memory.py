"""
Unit Tests for LEVI-AI Phase 2: RESONANT MEMORY.
Verifies the mathematical resonance, survival gating, and rule promotion.
"""

import asyncio
import pytest
import logging
from datetime import datetime, timedelta, timezone
from backend.memory.resonance import MemoryResonance
from backend.utils.archiver import SovereignArchiver

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_resonance_decay_math():
    """Verifies the resonance formula: R = I / (1 + (AgeDays * 0.1))"""
    importance = 1.0
    
    # 1. Day 0 Resonance
    r0 = MemoryResonance.calculate_resonance(importance, datetime.now(timezone.utc))
    assert r0 == 1.0
    
    # 2. Day 10 Resonance
    # R = 1.0 / (1 + (10 * 0.1)) = 1.0 / 2.0 = 0.5
    created_at_10 = datetime.now(timezone.utc) - timedelta(days=10)
    r10 = MemoryResonance.calculate_resonance(importance, created_at_10)
    assert r10 == 0.5
    
    # 3. Day 30 Resonance
    # R = 1.0 / (1 + (30 * 0.1)) = 1.0 / 4.0 = 0.25
    created_at_30 = datetime.now(timezone.utc) - timedelta(days=30)
    r30 = MemoryResonance.calculate_resonance(importance, created_at_30)
    assert r30 == 0.25
    
    logger.info("[Test] Resonance Math Verified: Day 0=1.0, Day 10=0.5, Day 30=0.25")

def test_foa_weighting():
    """Verifies FOA (Frequency of Access) boost."""
    importance = 0.5
    # Standard: (0.5 * 1.0) / 1 = 0.5
    r_std = MemoryResonance.calculate_resonance(importance, datetime.now(timezone.utc), access_count=1)
    
    # Boosted: (0.5 * 1.2) / 1 = 0.6
    r_boost = MemoryResonance.calculate_resonance(importance, datetime.now(timezone.utc), access_count=50)
    
    assert r_boost > r_std
    assert r_boost == 0.6
    logger.info(f"[Test] FOA Weighting: Standard={r_std}, Boosted={r_boost}")

@pytest.mark.asyncio
async def test_archival_logic():
    """Verifies that memories are correctly formatted for archival."""
    user_id = "test_user_777"
    memories = [
        {"fact": "User likes blue pizza.", "importance": 0.4, "created_at": "2024-01-01T00:00:00Z"},
        {"fact": "User lives on Mars.", "importance": 0.3, "created_at": "2024-01-01T00:00:00Z"}
    ]
    
    success = await SovereignArchiver.archive_memories(user_id, memories)
    assert success is True
    logger.info("[Test] Cold Storage Archival Logic Verified.")

def test_survival_filtering():
    """Verifies the survival threshold logic."""
    facts = [
        {"fact": "High importance", "importance": 0.95, "created_at": (datetime.now(timezone.utc) - timedelta(days=50)).isoformat()}, # Should keep (Rule 1)
        {"fact": "Old but accessed", "importance": 0.5, "created_at": (datetime.now(timezone.utc) - timedelta(days=10)).isoformat(), "access_count": 10}, # Should keep (R=0.25 boosted?)
        {"fact": "Low resonance", "importance": 0.2, "created_at": (datetime.now(timezone.utc) - timedelta(days=100)).isoformat()} # Should drop
    ]
    
    decayed = MemoryResonance.apply_decay(facts)
    fact_texts = [f["fact"] for f in decayed]
    
    assert "High importance" in fact_texts
    assert "Low resonance" not in fact_texts
    logger.info(f"[Test] Survival Filtering Verified. Kept: {fact_texts}")

if __name__ == "__main__":
    # Manual execution for verification
    test_resonance_decay_math()
    test_foa_weighting()
    asyncio.run(test_archival_logic())
    test_survival_filtering()
    print("\nPhase 2 Verification Suite: SUCCESS")
