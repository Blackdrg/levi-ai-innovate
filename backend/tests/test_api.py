"""API Tests."""
import sys
sys.path.append('.')

from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

try:
    from backend.main import app
except ImportError:
    from main import app

app_client = TestClient(app)

def test_health(app_client):
    """Test health."""
    resp = app_client.get('/health')
    assert resp.status_code == 200
    assert resp.json()['status'] == 'ok'

@patch('backend.main.get_db')
@patch('backend.main.requests.post')
def test_chat(mock_req, mock_db, app_client):
    """Test chat."""
    mock_db.return_value = [MagicMock()]
    mock_req.return_value.status_code = 200
    mock_req.return_value.json.return_value = [{'text': 'hi'}]
    resp = app_client.post('/chat', json={'session_id': '1', 'message': 'hi'})
    assert resp.status_code == 200

@patch('backend.main.get_db')
def test_search_quotes(mock_db, app_client):
    """Test search."""
    resp = app_client.post('/search_quotes', json={'text': 'test'})
    assert resp.status_code == 200

@patch('backend.main.get_db')
def test_analytics(mock_db, app_client):
    """Test analytics."""
    resp = app_client.get('/analytics')
    assert resp.status_code == 200
