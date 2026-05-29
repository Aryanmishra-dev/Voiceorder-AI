"""Tests for dashboard routes."""

from fastapi.testclient import TestClient


def test_dashboard_requires_auth(client: TestClient):
    """Dashboard must reject anonymous requests."""
    response = client.get("/dashboard")
    assert response.status_code == 401


def test_dashboard_with_api_key_auth(client: TestClient, auth_headers: dict[str, str]):
    """Dashboard should render for authenticated admin requests."""
    response = client.get("/dashboard", headers=auth_headers)
    assert response.status_code == 200
    assert "AI BOT SERVICE" in response.text
