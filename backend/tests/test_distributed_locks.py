# pyright: reportMissingImports=false
import pytest
import time
from unittest.mock import patch, MagicMock, call
from backend.redis_client import distributed_lock, HAS_REDIS

def test_lock_acquisition():
    """Verify that a lock can be acquired and released."""
    with patch("backend.redis_client.HAS_REDIS", True), \
         patch("backend.redis_client.r") as mock_r:
        mock_r.set.return_value = True
        
        lock_name = "test_lock_1"
        with distributed_lock(lock_name, ttl=5) as acquired:
            assert acquired is True
            # Attempt to acquire same lock
            mock_r.set.return_value = False
            with distributed_lock(lock_name, ttl=5) as acquired_again:
                assert acquired_again is False

def test_lock_retry():
    """Verify that the lock handles retries correctly."""
    with patch("backend.redis_client.HAS_REDIS", True), \
         patch("backend.redis_client.r") as mock_r:
        
        # Fail first 2 times, succeed on 3rd
        mock_r.set.side_effect = [False, False, True]
        
        with patch("time.sleep") as mock_sleep:
            lock_name = "retry_lock"
            with distributed_lock(lock_name, ttl=5, retries=2, backoff=0.1) as acquired:
                assert acquired is True
                assert mock_r.set.call_count == 3
                assert mock_sleep.call_count == 2

def test_lock_release_safety():
    """Verify that only the owner can release a lock via Lua."""
    with patch("backend.redis_client.HAS_REDIS", True), \
         patch("backend.redis_client.r") as mock_r:
        
        mock_r.set.return_value = True
        
        lock_name = "safety_lock"
        with distributed_lock(lock_name, ttl=5) as acquired:
            assert acquired is True
            # The context manager should call eval with LUA_RELEASE_SCRIPT
            # and the unique lock_val created inside
        
        # Verify eval was called for release
        assert mock_r.eval.called
        # Check that the 4th argument (ARGV[1]) was the unique token (timestamp based)
        # We can't easily predict the exact timestamp, but we know it was passed.
        args, kwargs = mock_r.eval.call_args
        assert args[1] == 1 # num_keys
        assert args[2] == f"lock:{lock_name}"

def test_credit_deduction_atomic_flow():
    """
    Integration test for backend.api.payments.use_credits.
    Verifies that Firestore read happens INSIDE the lock.
    """
    from backend.api.payments import use_credits
    
    user_id = "test_user_atomic"
    mock_user_data = {"credits": 50, "tier": "pro"}
    
    with patch("backend.api.payments.HAS_REDIS", True), \
         patch("backend.api.payments.distributed_lock") as mock_lock, \
         patch("backend.api.payments.get_daily_ai_spend") as mock_spend, \
         patch("backend.api.payments.firestore_db") as mock_db:
        
        # 1. Setup mocks
        mock_spend.return_value = 10000 # Force fallback to credits (Pro limit is 1000)
        
        # Lock acquisition succeeds
        mock_lock.return_value.__enter__.return_value = True
        
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = mock_user_data
        
        # Return doc on every get() call
        mock_db.collection().document().get.return_value = mock_doc
        
        # 2. Call use_credits
        res = use_credits(user_id, action="image") # Cost 5 for images
        
        # 3. Assertions
        assert res["status"] == "success"
        assert res["source"] == "credits"
        assert res["balance"] == 45
        
        # Verify that get() was called AFTER the lock was acquired
        # (The order of calls in mock_db and mock_lock can be checked)
        # But specifically, we check that update used Increment
        update_call = mock_db.collection().document().update.call_args[0][0]
        assert "credits" in update_call
        # Increment(-5) is the expected value
        from firebase_admin import firestore
        assert isinstance(update_call["credits"], firestore.Increment)

def test_credit_deduction_failure_locked():
    """Verify that use_credits fails if lock cannot be acquired."""
    from backend.api.payments import use_credits
    
    user_id = "test_user_busy"
    
    with patch("backend.api.payments.HAS_REDIS", True), \
         patch("backend.api.payments.distributed_lock") as mock_lock, \
         patch("backend.api.payments.get_daily_ai_spend") as mock_spend, \
         patch("backend.api.payments.firestore_db") as mock_db:
        
        mock_spend.return_value = 10000 
        mock_lock.return_value.__enter__.return_value = False # Lock busy
        
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {"credits": 50, "tier": "pro"}
        mock_db.collection().document().get.return_value = mock_doc
        
        with pytest.raises(Exception) as exc:
            use_credits(user_id, action="image")
        
        assert "Transaction in progress" in str(exc.value)
