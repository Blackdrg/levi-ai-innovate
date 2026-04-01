import pytest
from backend.auth import TIERS, check_allowance
from backend.db.redis_client import incr_daily_ai_spend, get_daily_ai_spend

@pytest.fixture
def mock_redis(monkeypatch):
    # simple in-memory mock for spend tracking
    _cache = {}
    def mock_incr(user_id, amount=1.0):
        key = f"spend:{user_id}"
        _cache[key] = _cache.get(key, 0.0) + amount
        return _cache[key]
    def mock_get(user_id):
        return _cache.get(f"spend:{user_id}", 0.0)
        
    monkeypatch.setattr("backend.db.redis_client.incr_daily_ai_spend", mock_incr)
    monkeypatch.setattr("backend.db.redis_client.get_daily_ai_spend", mock_get)
    monkeypatch.setattr("backend.db.redis_client.get_user_credits", lambda uid: 0)
    return _cache

def test_free_tier_allowance(mock_redis):
    user_id = "test_free_user"
    tier = "free"
    limit = TIERS[tier]["daily_limit"]
    
    # Under limit
    assert check_allowance(user_id, tier, cost=1) is True
    
    # Reach limit
    incr_daily_ai_spend(user_id, float(limit))
    
    # Over limit
    assert check_allowance(user_id, tier, cost=1) is False

def test_pro_tier_allowance(mock_redis):
    user_id = "test_pro_user"
    tier = "pro"
    limit = TIERS[tier]["daily_limit"] # 1000
    
    # 500 units should be fine
    incr_daily_ai_spend(user_id, 500.0)
    assert check_allowance(user_id, tier, cost=1) is True
    
    # 1001 units should fail
    incr_daily_ai_spend(user_id, 501.0)
    assert check_allowance(user_id, tier, cost=1) is False

def test_credit_fallback(monkeypatch, mock_redis):
    user_id = "test_fallback_user"
    tier = "free"
    
    # Limit reached
    incr_daily_ai_spend(user_id, 100.0)
    
    # Mock credits available
    monkeypatch.setattr("backend.db.redis_client.get_user_credits", lambda uid: 10)
    
    # Should be True due to credit fallback
    assert check_allowance(user_id, tier, cost=5) is True
    
    # Should be False if cost > credits
    assert check_allowance(user_id, tier, cost=20) is False
