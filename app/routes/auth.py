from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from app.auth import SECRET, verify_token
from app.db.postgres import get_db_pool
from jose import jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta

router = APIRouter(prefix="/api/v13/auth", tags=["Auth"])
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class AuthRequest(BaseModel):
    email: EmailStr
    password: str

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(days=7))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET, algorithm="HS256")

@router.post("/register")
async def register(req: AuthRequest):
    pool = await get_db_pool()
    hashed = pwd_context.hash(req.password)
    async with pool.acquire() as conn:
        try:
            await conn.execute(
                "INSERT INTO users (email, hashed_password) VALUES ($1, $2)",
                req.email, hashed
            )
            return {"message": "Node registration successful."}
        except Exception as e:
            raise HTTPException(status_code=400, detail="Node identifier already exists.")

@router.post("/login")
async def login(req: AuthRequest):
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        user = await conn.fetchrow("SELECT * FROM users WHERE email = $1", req.email)
        if not user or not pwd_context.verify(req.password, user["hashed_password"]):
            raise HTTPException(status_code=401, detail="Invalid security key.")
        
        token = create_access_token({"sub": user["email"], "uid": str(user["id"])})
        return {"access_token": token, "token_type": "bearer", "user": {"email": user["email"]}}

@router.get("/me")
async def me(payload = Depends(verify_token)):
    return payload
