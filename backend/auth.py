# pyright: reportMissingImports=false

"""

Auth utilities — JWT creation, password hashing, token verification.

Routes (/token, /register) live in main.py.

This module is importable without a FastAPI app instance.

"""

from fastapi import Depends, HTTPException, status, Request  # type: ignore

from fastapi.security import OAuth2PasswordBearer  # type: ignore

from jose import JWTError, jwt # type: ignore

from passlib.context import CryptContext # type: ignore

from datetime import datetime, timedelta

from typing import Optional, Any

import os

from dotenv import load_dotenv  # type: ignore

from pydantic import BaseModel  # type: ignore
from sqlalchemy.orm import Session  # type: ignore
try:
    from backend.db import get_db  # type: ignore
    from backend.models import Users  # type: ignore
except (ImportError, ModuleNotFoundError):
    from db import get_db  # type: ignore
    from models import Users  # type: ignore



load_dotenv()



SECRET_KEY = os.environ["SECRET_KEY"]

ALGORITHM = "HS256"

ACCESS_TOKEN_EXPIRE_MINUTES = 30



pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)

def get_token(request: Request, header_token: Optional[str] = Depends(oauth2_scheme)) -> str:
    """
    Extract token from Authorization header or 'access_token' cookie.
    """
    if header_token:
        return header_token
    
    cookie_token = request.cookies.get("access_token")
    if cookie_token:
        return cookie_token
        
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )





class Token(BaseModel):

    access_token: str

    token_type: str





class User(BaseModel):

    username: str





def verify_password(plain_password: str, hashed_password: str) -> bool:

    return pwd_context.verify(plain_password, hashed_password)





def get_password_hash(password: str) -> str:

    return pwd_context.hash(password)





import uuid

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    jti = str(uuid.uuid4())
    to_encode.update({"exp": expire, "jti": jti, "type": "access"})

    # Store JTI in Redis whitelist so logout (delete_jti) actually revokes it.
    try:
        from backend.redis_client import store_jti  # type: ignore
    except ImportError:
        from redis_client import store_jti  # type: ignore

    delta = expires_delta or timedelta(minutes=15)
    seconds = int(delta.total_seconds())
    store_jti(jti, seconds)

    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)  # type: ignore


def create_refresh_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Issue a long-lived refresh token (default 30 days).
    Stored under 'refresh_jti:{jti}' in Redis so it can be revoked on use
    (rotation) or on logout.
    """
    to_encode = data.copy()
    delta = expires_delta or timedelta(days=30)
    expire = datetime.utcnow() + delta
    jti = str(uuid.uuid4())
    to_encode.update({"exp": expire, "jti": jti, "type": "refresh"})

    try:
        from backend.redis_client import _set  # type: ignore
    except ImportError:
        from redis_client import _set  # type: ignore

    # Use a distinct key prefix so refresh JTIs cannot be confused with access JTIs.
    _set(f"refresh_jti:{jti}", "1", ex=int(delta.total_seconds()))

    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)  # type: ignore



async def get_current_user(token: str = Depends(get_token), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM]) # type: ignore
        jti = payload.get("jti")
        if not jti:
             raise credentials_exception
             
        try:
            from backend.redis_client import is_jti_blacklisted  # type: ignore
        except ImportError:
            from redis_client import is_jti_blacklisted  # type: ignore
            
        if is_jti_blacklisted(jti):
             raise credentials_exception

        username_val: Any = payload.get("sub")
        if username_val is None:
            raise credentials_exception
        username: str = str(username_val)
    except JWTError:
        raise credentials_exception
    
    user = db.query(Users).filter(Users.username == username).first()
    if user is None:
        raise credentials_exception
    return user

