import pytest
import httpx
from backend.api.main import app

@pytest.fixture
async def async_client():
    """
    Sovereign Async Client (Graduation v13.0).
    Uses ASGITransport to test the full stack without needing a live network socket.
    """
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), 
        base_url="http://localhost:8000"
    ) as client:
        yield client
