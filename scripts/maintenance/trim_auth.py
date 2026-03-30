import os

with open("backend/main.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

new_lines = []
skip = False

for line in lines:
    # 1. Skip OAuth and Session Middleware
    if line.strip() == "# Essential Session Middleware for OAuth":
        skip = "oauth_block"
    if skip == "oauth_block" and line.startswith("@app.on_event(\"startup\")"):
        skip = False

    # 2. Skip Register, Login, and Password Reset endpoints
    if line.startswith("@app.post(\"/register\")"):
        skip = "register_block"
    if skip == "register_block" and line.strip() == "# Phase 2: Viral Loops & Engagement":
        skip = False

    # 3. Replace Legacy Token & CryptContext block with Firebase Admin
    if line.startswith("SECRET_KEY = os.environ[\"SECRET_KEY\"]"):
        skip = "jwt_block"
        new_lines.append('''SECRET_KEY = os.environ.get("SECRET_KEY", "fallback")
CLIENT_KEY = os.getenv("CLIENT_KEY")

import firebase_admin # type: ignore
from firebase_admin import auth as firebase_auth # type: ignore
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials # type: ignore

if not firebase_admin._apps:
    try:
        firebase_admin.initialize_app()
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Firebase init error: {e}")

security = HTTPBearer()

async def get_current_user(cred: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        decoded_token = firebase_auth.verify_id_token(cred.credentials)
        uid = decoded_token.get("uid")
        email = decoded_token.get("email")
        if not uid: raise credentials_exception
        
        user = db.query(Users).filter(Users.email == email).first()
        if not user:
            base_username = email.split('@')[0] if email else f"user_{uid[:8]}"
            username = base_username
            counter = 1
            while db.query(Users).filter(Users.username == username).first():
                username = f"{base_username}{counter}"
                counter += 1
            user = Users(username=username, email=email)
            db.add(user)
            db.commit()
            db.refresh(user)
        return user
    except Exception:
        raise credentials_exception

async def get_current_user_optional(cred: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False)), db: Session = Depends(get_db)):
    if not cred: return None
    try:
        decoded_token = firebase_auth.verify_id_token(cred.credentials)
        email = decoded_token.get("email")
        if not email: return None
        return db.query(Users).filter(Users.email == email).first()
    except Exception:
        return None
\n''')
        continue

    if skip == "jwt_block" and line.startswith("async def verify_admin(request: Request):"):
        skip = False

    if not skip:
        new_lines.append(line)

with open("backend/main.py", "w", encoding="utf-8") as f:
    f.writelines(new_lines)
print("Successfully transitioned backend endpoints to Firebase Auth!")
