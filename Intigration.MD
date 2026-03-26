# LEVI — Full Integration Guide

## What was broken & what was fixed

| Issue | Root Cause | Fix |
|-------|-----------|-----|
| Login didn't persist | Backend sets httpOnly cookie, but JS tried to read `levi_token` from localStorage | `auth.html` now calls `/users/me` after login and stores user **display data** (not tokens) in localStorage |
| Chat 401 errors | `chat.js` sent `Authorization: Bearer <null>` header | Removed all manual headers — cookies are sent automatically via `credentials:'include'` |
| Backend unreachable on page load | No auto-connect logic | `auth-manager.js` pings `/health` on every page load |
| Nav showed "Sign In" when logged in | User info never stored | `auth-manager.js` reads cached user and updates nav |
| Studio / Gallery broken | Same token issue + wrong API_BASE | `studio.js` now uses cookie auth |

---

## Files to deploy

Copy these files to your project:

```
frontend/js/auth-manager.js   ← NEW — load on every page
frontend/js/api.js            ← UPDATED — cookie-based, no tokens
frontend/js/chat.js           ← UPDATED — cookie-based
frontend/js/studio.js         ← UPDATED — cookie-based
frontend/auth.html            ← UPDATED — stores profile after login
backend/entrypoint.sh         ← UPDATED — runs migrations on start
```

---

## How to add `auth-manager.js` to every HTML page

Add **before** the closing `</body>` tag on every page:

```html
<script src="js/auth-manager.js"></script>
```

It handles:
- `window.API_BASE` detection (localhost vs production)
- Pinging `/health` every 30 s
- Updating the nav button (Sign In ↔ username)
- Refreshing user profile silently

---

## How the auth flow works now

```
User fills auth.html form
        ↓
POST /login  (JSON body, credentials:'include')
        ↓
Backend sets httpOnly cookie (access_token + refresh_token)
        ↓
Browser auto-sends cookies on every subsequent request
        ↓
auth.html calls GET /users/me to get profile for display
        ↓
Stores { id, username, email, tier, credits } in localStorage
        ↓
Redirects to studio.html
```

**Important:** The actual JWT is **never accessible to JavaScript** (httpOnly). Only non-sensitive display data is stored in localStorage.

---

## Local development quick start

```bash
# 1. Install dependencies
cd backend && pip install -r requirements.txt

# 2. Copy environment
cp .env.example .env.local
# Edit .env.local — at minimum set SECRET_KEY

# 3. Run migrations + server
alembic upgrade head
python seed.py
uvicorn main:app --host 0.0.0.0 --port 8000

# 4. Serve frontend (new terminal)
python -m http.server 8080 --directory frontend

# 5. Visit http://localhost:8080
```

Or use the all-in-one runner:
```bash
python run_app.py
```

---

## Production (Firebase Hosting + Cloud Run)

1. **Backend** → Google Cloud Run, Docker, `Dockerfile`
   - Set all env vars in Google Cloud Console
   - Port 8080 is standard (automatically handled by Cloud Run)

2. **Frontend** → Firebase Hosting
   - `firebase.json` rewrites `/api/*` → your `levi-backend` service
   - The `API_BASE` in `api.js` auto-detects this

---

## Testing the connection

Open browser DevTools → Console after loading any page. You should see:

```
[LEVI] API Base: http://localhost:8000   (local)
[LEVI] Backend status: ok
```

The nav button will show your username when logged in, and the green dot indicates the backend is reachable.

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| CORS errors in console | Check `CORS_ORIGINS` in backend env vars matches your frontend URL |
| 401 on every request | Clear cookies (`Application → Cookies → Clear`) and log in again |
| `API_BASE` points to wrong host | `auth-manager.js` must be loaded before `api.js` on every page |
| Login succeeds but profile not stored | Check `/users/me` returns 200 — may need email verification first |