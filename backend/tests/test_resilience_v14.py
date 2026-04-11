import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from backend.utils.llm_utils import _async_call_llm_api
from backend.db.neo4j_connector import Neo4jStore
from backend.utils.network import neo4j_breaker

@pytest.mark.asyncio
async def test_llm_fallback_routing():
    """Verify local -> cloud fallback logic."""
    # 1. Mock call_ollama_llm to simulate failure
    with patch("backend.utils.llm_utils.call_ollama_llm", new_callable=AsyncMock) as mock_ollama:
        mock_ollama.return_value = "Local brain offline. Searching for cloud fallback..."
        
        # 2. Mock call_cloud_fallback to verify it is called
        with patch("backend.utils.llm_utils.call_cloud_fallback", new_callable=AsyncMock) as mock_cloud:
            mock_cloud.return_value = "Cloud response"
            
            res = await _async_call_llm_api([{"role": "user", "content": "hi"}])
            
            assert res == "Cloud response"
            mock_ollama.assert_called_once()
            mock_cloud.assert_called_once()

@pytest.mark.asyncio
async def test_neo4j_circuit_breaker():
    """Verify Neo4j breaker trips after failures."""
    # Reset breaker state
    neo4j_breaker.state = "CLOSED"
    neo4j_breaker.failures = 0
    
    store = Neo4jStore()
    
    # Mock connect to fail
    with patch.object(store, "connect", side_effect=Exception("DB Down")):
        # Call multiple times to trip breaker
        for _ in range(3):
            try:
                # We expect upsert_triplet to raise but we want to see the breaker state
                await store.upsert_triplet(MagicMock())
            except:
                pass
        
        assert neo4j_breaker.state == "OPEN"
        
        # Next call should fail immediately without trying connect
        with pytest.raises(RuntimeError, match="Circuit NEO4J is OPEN"):
            await store.upsert_triplet(MagicMock())

@pytest.mark.asyncio
async def test_cloud_task_dispatcher_logic():
    """Verify CloudTaskDispatcher constructs the correct task structure."""
    from backend.utils.cloud_tasks import CloudTaskDispatcher
    
    with patch("google.cloud.tasks_v2.CloudTasksClient") as mock_client:
        dispatcher = CloudTaskDispatcher()
        dispatcher.project = "test-project"
        dispatcher.webhook_url = "https://api.test.com/webhook"
        
        dispatcher.enqueue_mission("MISSION-123", {"goal": "test"})
        
        # Check if create_task was called
        mock_client.return_value.create_task.assert_called_once()
        args, kwargs = mock_client.return_value.create_task.call_args
        task = kwargs["request"]["task"]
        
        assert task["http_request"]["url"] == "https://api.test.com/webhook"
        assert "oidc_token" in task["http_request"]
        assert task["http_request"]["oidc_token"]["audience"] == "https://api.test.com/webhook"

@pytest.mark.asyncio
async def test_internal_webhook_handler():
    """Verify main.py webhook routes to tasks correctly."""
    from backend.main import app
    from httpx import AsyncClient
    
    with patch("backend.main.execute_mission_from_cloud_task", new_callable=AsyncMock) as mock_exec:
        mock_exec.return_value = True
        
        async with AsyncClient(app=app, base_url="http://test") as ac:
            response = await ac.post(
                "/api/v1/internal/tasks/mission_handler",
                json={"mission_id": "M-1", "payload": {"foo": "bar"}}
            )
            
        assert response.status_code == 200
        assert response.json()["status"] == "success"
        mock_exec.assert_called_once_with("M-1", {"foo": "bar"})
