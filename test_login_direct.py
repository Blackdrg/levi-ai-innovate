import os
import sys
import asyncio
from fastapi import Request

# Setup environment
from dotenv import load_dotenv
load_dotenv(".env.local", override=True)
sys.path.insert(0, os.path.join(os.getcwd(), "backend"))

from backend.db import SessionLocal
from backend.main import login_json, UserIn

async def test():
    db = SessionLocal()
    try:
        print("[Test] Calling login_json natively...")
        scope = {
            "type": "http",
            "method": "POST",
            "headers": [(b"content-type", b"application/json")]
        }
        req = Request(scope)
        user_data = UserIn(username="testuser_febe08ad", password="password123")
        res = await login_json(request=req, user_in=user_data, db=db)
        print("Success:", res)
    except Exception as e:
        import traceback
        traceback.print_exc()
    finally:
        db.close()

asyncio.run(test())
