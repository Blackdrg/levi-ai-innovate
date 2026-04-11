import os
import pytest
import asyncio
import json
from unittest.mock import MagicMock, patch
from backend.core.orchestrator import Orchestrator
from backend.core.dcn.gossip import DCNGossip
from backend.db.models import AuditLog
from backend.services.health_monitor import AutonomousHealthMonitor
from backend.core.execution_state import CentralExecutionState, MissionState

@pytest.mark.asyncio
async def test_dcn_secret_enforcement():
    """Verify DCN_SECRET is mandatory and checked for length."""
    with patch.dict(os.environ, {"DCN_SECRET": ""}):
        with pytest.raises(RuntimeError, match="DCN_SECRET is mandatory"):
            # Re-import or re-initialize to trigger check
            import importlib
            import backend.core.dcn.gossip
            importlib.reload(backend.core.dcn.gossip)

@pytest.mark.asyncio
async def test_audit_hmac_chaining():
    """Verify AuditLog uses HMAC-SHA256 for chaining."""
    prev_checksum = "genesis"
    row_data = {"event": "test"}
    
    with patch.dict(os.environ, {"AUDIT_CHAIN_SECRET": "test_secret"}):
        checksum = AuditLog.calculate_checksum(prev_checksum, row_data)
        # Verify it's not a simple SHA256 (which would be different)
        import hmac, hashlib
        msg = f"genesis:{json.dumps(row_data, sort_keys=True)}".encode()
        expected = hmac.new(b"test_secret", msg, hashlib.sha256).hexdigest()
        assert checksum == expected

@pytest.mark.asyncio
async def test_orchestrator_vram_caps():
    """Verify Orchestrator respects hard VRAM caps."""
    orchestrator = Orchestrator()
    
    with patch("backend.utils.metrics.VRAM_AVAILABLE._value.get", return_value=100*1024*1024): # 100MB left
        with patch.dict(os.environ, {"GPU_VRAM_TOTAL_MB": "8192"}):
            pressure = await orchestrator.check_vram_pressure()
            assert pressure == 1.0 # Should trigger emergency pressure

@pytest.mark.asyncio
async def test_health_monitor_rollback_trigger():
    """Verify HealthMonitor triggers rollback when thresholds are breached."""
    monitor = AutonomousHealthMonitor()
    monitor.FAIL_THRESHOLD = 1
    
    # Mock dependencies
    with patch("backend.services.ollama_health.ollama_monitor.check_health", return_value={"status": "offline"}):
        with patch("backend.services.rollback_service.rollback_service.trigger_emergency_rollback") as mock_rollback:
            await monitor._perform_checks()
            mock_rollback.assert_called_once_with(user_id="SYSTEM_AUTONOMOUS", reason="Autonomous Rollback: OLLAMA failure threshold exceeded.")

@pytest.mark.asyncio
async def test_hybrid_hydration():
    """Verify hybrid hydration prefers Redis but falls back to SQL."""
    with patch("backend.core.execution_state.HAS_REDIS", False):
        with patch("backend.db.postgres.PostgresDB.get_session") as mock_session:
            # Mock Postgres returning one active mission
            mock_m = MagicMock()
            mock_m.mission_id = "SQL_MISSION"
            mock_m.status = MissionState.EXECUTING.value
            mock_m.payload = None
            
            mock_res = MagicMock()
            mock_res.scalars().all.return_value = [mock_m]
            
            async_mock_session = MagicMock()
            async_mock_session.execute.return_value = mock_res
            mock_session.return_value.__aenter__.return_value = async_mock_session
            
            active = await CentralExecutionState.load_state_on_boot()
            assert "SQL_MISSION" in active
            assert active["SQL_MISSION"]["state"] == MissionState.EXECUTING.value

if __name__ == "__main__":
    # This script is intended to be run via pytest
    pass
