import requests
import sys
import uuid

API_BASE = "http://localhost:8000"
session = requests.Session()

# Add a random suffix to avoid 400 Already Exists
user_random = "testuser_" + str(uuid.uuid4())[:8] + "@example.com"
pwd = "password123"

print(f"1. Registering dummy user ({user_random})...")
res = session.post(f"{API_BASE}/register", json={"username": user_random, "password": pwd})
if res.status_code not in (200, 400):
    print(f"FAILED to register: {res.status_code} {res.text}")
    sys.exit(1)

print("2. Logging in...")
res = session.post(f"{API_BASE}/login", json={"username": user_random, "password": pwd})
if res.status_code != 200:
    print(f"FAILED to login: {res.status_code} {res.text}")
    sys.exit(1)

cookies = session.cookies.get_dict()
print(f"SUCCESS login:")
for name, val in cookies.items():
    print(f"  Cookie Name: {name} (Value hidden for security)")

if "access_token" not in cookies:
    print("FAILED: No access_token cookie received from backend setting httpOnly cookies.")
    sys.exit(1)

print("3. Fetching user profile via httpOnly Cookie...")
res = session.get(f"{API_BASE}/users/me")
if res.status_code != 200:
    print(f"FAILED to fetch profile: {res.status_code} {res.text}")
    sys.exit(1)

data = res.json()
print(f"SUCCESS fetched profile! Logged in as: {data.get('username')}, Tier: {data.get('tier')}")

print("\n✓ AUTHENTICATION FLOW VERIFIED")
