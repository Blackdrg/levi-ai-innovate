# pyright: reportMissingImports=false
"""API Tests - Hardened for v6.8 Sovereign mind."""
import sys
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

# Ensure backend can be imported
sys.path.append('.')

from backend.main import app

@pytest.fixture
def app_client():
    return TestClient(app)

def test_health(app_client):
    """Test the Sovereign Engine Probe."""
    resp = app_client.get('/health')
    assert resp.status_code == 200
    # v6.8 returns "ready" or "degraded"
    assert resp.json()['status'] in ('ready', 'degraded')
    assert 'engines' in resp.json()

@patch('backend.api.chat.run_orchestrator')
def test_chat(mock_orch, app_client):
    """Test the v6.8 Chat Orchestrator endpoint."""
    mock_orch.return_value = {
        "response": "Hello traveler.",
        "intent": "chat",
        "route": "local",
        "request_id": "test_req_123"
    }
    
    # Prefix is /chat in main.py
    resp = app_client.post('/chat', json={'message': 'hi', 'session_id': '1'})
    assert resp.status_code == 200
    assert resp.json()['response'] == "Hello traveler."

@patch('backend.api.search.run_orchestrator')
def test_search(mock_orch, app_client):
    """Test the v6.8 Search Orchestrator endpoint."""
    mock_orch.return_value = {
        "response": "The cosmos is vast.",
        "intent": "search",
        "route": "api",
        "request_id": "test_req_456"
    }
    
    # Refactored from /search_quotes to /search
    resp = app_client.post('/search', json={'query': 'universe', 'session_id': '2'})
    assert resp.status_code == 200
    assert resp.json()['answer'] == "The cosmos is vast."

def test_analytics(app_client):
    """Test the v6.8 Analytics endpoint."""
    # Prefix is /system/analytics in main.py
    # We use a mocked Firestore call inside the handler if needed, 
    # but here we just check connectivity
    resp = app_client.get('/system/analytics')
    assert resp.status_code in (200, 503) # 503 if firestore/redis are offline
