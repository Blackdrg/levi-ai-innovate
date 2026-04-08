from __future__ import annotations

from datetime import datetime, timedelta, timezone
import os

import httpx
import jwt
import pytest
from fastapi import FastAPI, Depends

os.environ.setdefault("ENVIRONMENT", "development")
os.environ.setdefault("TEST_MODE", "true")

from backend.auth.jwt_provider import JWTProvider
from backend.services.auth.logic import require_role, SovereignRole


def _make_app() -> FastAPI:
    app = FastAPI()

    @app.get("/auditor", dependencies=[Depends(require_role(SovereignRole.AUDITOR))])
    async def auditor_route():
        return {"ok": True}

    return app


@pytest.mark.asyncio
async def test_protected_route_rejects_missing_token():
    app = _make_app()
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/auditor")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_protected_route_rejects_expired_token(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "development")
    app = _make_app()
    expired = jwt.encode(
        {
            "sub": "user-1",
            "jti": "expired-jti",
            "role": "auditor",
            "tier": "pro",
            "type": "identity",
            "exp": datetime.now(timezone.utc) - timedelta(minutes=1),
        },
        JWTProvider.SECRET_KEY,
        algorithm=JWTProvider.ALGORITHM,
    )
    headers = {"Authorization": f"Bearer {expired}"}
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/auditor", headers=headers)
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_protected_route_rejects_wrong_role(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "development")
    app = _make_app()
    tokens = JWTProvider.create_token_pair(
        "user-1",
        {"email": "user@example.com", "role": "user", "tier": "pro"},
    )
    headers = {"Authorization": f"Bearer {tokens['identity_token']}"}
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/auditor", headers=headers)
    assert response.status_code == 403
