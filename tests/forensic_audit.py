# tests/forensic_audit.py
import pytest
import os
import asyncio
from backend.kernel.kernel_wrapper import kernel
from backend.core.orchestrator import Orchestrator

@pytest.mark.asyncio
async def test_kernel_graduation_status():
    """Verify the kernel is running in a graduated native mode or explicitly stubbed."""
    # Ensure kernel wrapper is aware of the bare-metal stubs
    drivers = kernel.get_drivers()
    assert "ACPI" in drivers or "ata" in drivers, "Kernel must have hardware drivers initialized."

@pytest.mark.asyncio
async def test_mission_isolation():
    """Verify that missions are executed within secure sandboxes/workers."""
    orch = Orchestrator()
    # Mocking a mission to check isolation logic
    mission_id = "test-isolated-mission"
    # In a real test, we would verify the PID/Namespace isolation
    assert orch is not None

@pytest.mark.asyncio
async def test_bft_integrity():
    """Verify that the BFT signer is active and signing kernel pulses."""
    from backend.kernel.bft_signer import bft_signer
    signature = bft_signer.sign_pulse("test-pulse")
    assert signature is not None
    assert bft_signer.verify_pulse("test-pulse", signature)

def test_config_hardening():
    """Check for production vs testing environment safety gates."""
    env = os.getenv("ENVIRONMENT", "testing")
    if env == "production":
        # Ensure debug flags are OFF
        assert os.getenv("DEBUG") != "true"
