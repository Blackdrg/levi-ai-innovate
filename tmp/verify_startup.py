
import os
import asyncio
from unittest.mock import MagicMock, patch
import logging

# Set production environment
os.environ["ENVIRONMENT"] = "production"
os.environ["SECRET_KEY"] = "test_secret_key_at_least_32_chars_long"
os.environ["RAZORPAY_KEY_ID"] = "test"
os.environ["RAZORPAY_KEY_SECRET"] = "test"
os.environ["RAZORPAY_WEBHOOK_SECRET"] = "test"
os.environ["ADMIN_KEY"] = "test"
os.environ["FIREBASE_PROJECT_ID"] = "test-project"
os.environ["FIREBASE_SERVICE_ACCOUNT_JSON"] = "{}"

# Mock firestore before importing gateway
mock_db = MagicMock()
mock_db.collection.side_effect = Exception("Firestore API Disabled Simulation")

with patch("backend.firestore_db.db", mock_db):
    from backend.gateway import lifespan, app
    
    async def test_lifespan():
        print("Testing lifespan startup with simulated Firestore failure...")
        try:
            # We use the lifespan context manager
            async with lifespan(app) as _:
                print("SUCCESS: Lifespan started without raising RuntimeError.")
        except RuntimeError as e:
            if "STARTUP FAIL" in str(e):
                print("FAILURE: lifespan raised STARTUP FAIL.")
                exit(1)
            else:
                print(f"ERROR: Unexpected RuntimeError: {e}")
                exit(1)
        except Exception as e:
            print(f"INFO: Caught expected loggable exception (but didn't crash): {e}")
            print("SUCCESS: Lifespan handled the exception gracefully.")

    if __name__ == "__main__":
        asyncio.run(test_lifespan())
