# pyright: reportMissingImports=false
import pytest
from unittest.mock import patch, MagicMock
from backend.services.analytics.router import get_performance_metrics

@pytest.mark.asyncio
async def test_performance_aggregation_logic():
    """Verify that performance metrics correctly aggregate from Redis lists."""
    mock_redis = MagicMock()
    # Simulated last 10 requests latency
    mock_redis.lrange.return_value = [b"100", b"150", b"200", b"250", b"300", b"400", b"500", b"600", b"700", b"1000"]
    mock_redis.get.side_effect = [b"1500", b"3"] # total_requests, error_count
    mock_redis.hgetall.return_value = {b"inst-1": b"1711680000"}
    
    with patch('backend.services.analytics.router.redis_client', mock_redis), \
         patch('backend.services.analytics.router.HAS_REDIS', True):
        
        # Act
        # Note: Depends(verify_admin) check is bypassed in unit tests by calling local function
        metrics = await get_performance_metrics(is_admin=True)
        
        # Assert
        assert metrics["total_requests"] == 1500
        assert metrics["active_instances"] == 1
        # p95 of [100...1000] should be around 865+
        assert metrics["p95_latency_ms"] > 800
        # error rate (3/1500 * 100) = 0.2
        assert metrics["error_rate_percent"] == 0.2

@pytest.mark.asyncio
async def test_performance_fallback_no_redis():
    """Verify graceful handling when Redis is unavailable."""
    with patch('backend.services.analytics.router.HAS_REDIS', False):
        metrics = await get_performance_metrics(is_admin=True)
        assert "error" in metrics
        assert metrics["status"] == "degraded"
