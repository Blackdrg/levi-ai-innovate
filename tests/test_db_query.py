import os
from dotenv import load_dotenv
load_dotenv(".env.local", override=True)



if __name__ == "__main__":
    from backend.db import SessionLocal
    from backend.models import Users
    db = SessionLocal()
    try:
        print("Executing User lookup...")
        existing = db.query(Users).filter(Users.username == "test@example.com").first()
        print("Database Query Succeeded! User:", existing)
    except Exception as e:
        import traceback
        traceback.print_exc()
    finally:
        db.close()
