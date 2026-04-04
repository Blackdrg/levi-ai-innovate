from fastapi import Depends, HTTPException, Query
from fastapi.security import HTTPBearer
from jose import JWTError, jwt
import os

SECRET = os.getenv("JWT_SECRET", "f7e7eac8b6679e3a6b651a6707de960ca07215a806216a3227b98f4bc3d5b3dd")
security = HTTPBearer()

def verify_token(creds = Depends(security)):
    try:
        payload = jwt.decode(creds.credentials, SECRET, algorithms=["HS256"])
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

# For SSE endpoints (EventSource can't set headers easily)
async def verify_token_query(token: str = Query(...)):
    try:
        payload = jwt.decode(token, SECRET, algorithms=["HS256"])
        # Mocking a user object with attributes
        class User:
            def __init__(self, data):
                for k, v in data.items():
                    setattr(self, k, v)
                self.uid = data.get("sub", data.get("uid", "anonymous"))
        return User(payload)
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
