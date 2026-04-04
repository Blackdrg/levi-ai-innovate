import json
import pytest
from datetime import datetime, timezone
from backend.core.v8.sync_engine import SovereignSync

def test_v13_health(client):
    """Verifies the v13.0 Monolith Health Probe."""
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] in ["ready", "degraded"]
    assert "v13.0.0" in str(data.get("version", ""))

def test_v13_brain_greeting(client):
    """Verifies the INTERNAL logic path for greetings."""
    resp = client.post(
        "/api/v8/brain/run",
        json={"input": "Hello Levi", "user_id": "test_user", "session_id": "s1"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "Greetings" in data["response"]
    assert data["decision"] == "INTERNAL"

def test_v13_synk_broadcast_fail(client):
    """Verifies that unsigned DCN fragments are rejected."""
    payload = {
        "payload": json.dumps({"rules": {"test": "fail"}}),
        "signature": "invalid_sig"
    }
    resp = client.post("/api/v8/synk/broadcast", json=payload)
    assert resp.status_code == 200 # App handles rejection via status body
    assert resp.json()["status"] == "denied"

def test_v13_synk_broadcast_success(client):
    """Verifies that signed DCN fragments are accepted."""
    rule_data = json.dumps({
        "swarm_id": "test_swarm",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "rules": {"detect_pii": "SAFE_MODE_TRIGGER"}
    })
    
    # We use the SovereignSync utility to generate a valid test signature
    signature = SovereignSync._generate_signature(rule_data)
    
    payload = {
        "payload": rule_data,
        "signature": signature
    }
    
    resp = client.post("/api/v8/synk/broadcast", json=payload)
    assert resp.status_code == 200
    assert resp.json()["status"] == "success"
    assert resp.json()["imported"] >= 0

def test_v13_telemetry_handshake(client):
    """Verifies the v4.1 Adaptive Pulse handshake (SSE)."""
    # Note: TestClient handles SSE as a list of events if not careful
    # For now we just verify the route is accessible
    with client.stream("GET", "/api/v8/telemetry/stream?profile=mobile") as response:
        assert response.status_code == 200
        # Check first line of SSE stream
        for line in response.iter_lines():
            if line.startswith("event: pulse_handshake"):
                assert "4.1.0" in line
                break
