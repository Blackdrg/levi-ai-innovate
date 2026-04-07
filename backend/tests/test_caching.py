# pyright: reportMissingImports=false
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_feed_cache_headers():
    """Verify Phase 42 SWR and ETag headers on the gallery feed."""
    response = client.get("/api/v1/gallery/feed")
    assert response.status_code == 200
    assert "Cache-Control" in response.headers
    assert "stale-while-revalidate" in response.headers["Cache-Control"]
    assert "ETag" in response.headers

def test_feed_etag_matching():
    """Verify that ETag matching returns 304 Not Modified."""
    # 1. Get the ETag
    res1 = client.get("/api/v1/gallery/feed")
    etag = res1.headers.get("ETag")
    assert etag is not None
    
    # 2. Request with If-None-Match
    res2 = client.get("/api/v1/gallery/feed", headers={"If-None-Match": etag})
    assert res2.status_code == 304

def test_gateway_vary_header():
    """Verify that the gateway enforces Vary isolation for Phase 42."""
    response = client.get("/health")
    assert "Vary" in response.headers
    assert "Accept-Encoding" in response.headers["Vary"]
    assert "X-Trace-ID" in response.headers["Vary"]

def test_daily_quote_swr():
    """Verify SWR on the daily quote endpoint."""
    response = client.get("/api/v1/gallery/daily_quote")
    assert "stale-while-revalidate" in response.headers.get("Cache-Control", "")
