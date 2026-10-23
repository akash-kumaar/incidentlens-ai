"""
Backend API and Engine tests for IncidentLens AI.
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.data.scenarios.scenario_data import ALL_SCENARIOS, SERVICES

client = TestClient(app)


def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "IncidentLens AI"
    assert "version" in data


def test_health_endpoint():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "timestamp" in data


def test_list_scenarios():
    response = client.get("/api/scenarios")
    assert response.status_code == 200
    scenarios = response.json()
    assert len(scenarios) == len(ALL_SCENARIOS)
    assert any(s["id"] == "scenario-deployment-regression" for s in scenarios)


def test_list_services():
    response = client.get("/api/services")
    assert response.status_code == 200
    services = response.json()
    assert len(services) == len(SERVICES)
    assert any(s["id"] == "api-gateway" for s in services)


def test_provider_status():
    response = client.get("/api/settings/provider")
    assert response.status_code == 200
    data = response.json()
    assert "provider" in data
    assert "bedrock_status" in data
    assert "s3_status" in data
    assert "demo_mode" in data


def test_create_and_fetch_investigation():
    payload = {
        "scenario_id": "scenario-deployment-regression",
        "service": "api-gateway",
        "incident_description": "Test regression incident",
        "depth": "standard",
    }
    create_res = client.post("/api/investigations", json=payload)
    assert create_res.status_code == 201
    inv_data = create_res.json()
    assert "id" in inv_data
    assert inv_data["service"] == "api-gateway"
    assert inv_data["scenario_id"] == "scenario-deployment-regression"

    fetch_res = client.get(f"/api/investigations/{inv_data['id']}")
    assert fetch_res.status_code == 200
    fetched = fetch_res.json()
    assert fetched["id"] == inv_data["id"]


def test_investigation_not_found():
    response = client.get("/api/investigations/non-existent-id")
    assert response.status_code == 404
