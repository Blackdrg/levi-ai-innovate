import pathlib

import yaml
from fastapi.testclient import TestClient

from backend.main import app


def test_health_reports_startup_contract():
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    payload = response.json()
    assert "startup" in payload
    assert "checks" in payload["startup"]
    assert payload["environment"] in ("development", "production")


def test_k8s_rollout_manifests_are_present_and_valid():
    deployment = pathlib.Path("backend/deployment/k8s/deployment.yaml")
    hpa = pathlib.Path("backend/deployment/k8s/hpa.yaml")
    pdb = pathlib.Path("backend/deployment/k8s/pdb.yaml")

    deployment_docs = list(yaml.safe_load_all(deployment.read_text(encoding="utf-8")))
    hpa_docs = list(yaml.safe_load_all(hpa.read_text(encoding="utf-8")))
    pdb_docs = list(yaml.safe_load_all(pdb.read_text(encoding="utf-8")))

    assert deployment_docs[0]["kind"] == "Deployment"
    assert deployment_docs[0]["spec"]["template"]["spec"]["containers"][0]["readinessProbe"]["httpGet"]["path"] == "/ready"
    assert hpa_docs[0]["kind"] == "HorizontalPodAutoscaler"
    assert pdb_docs[0]["kind"] == "PodDisruptionBudget"
