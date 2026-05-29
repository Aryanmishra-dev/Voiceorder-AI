"""Tests for webhook and health endpoints."""

from fastapi.testclient import TestClient


def test_health_check_public(client: TestClient):
    """Health endpoint should remain publicly reachable."""
    response = client.get("/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert "timestamp" in payload


def test_webhook_missing_body_returns_ok(client: TestClient):
    """Webhook should ignore malformed payloads without failing Twilio retries."""
    response = client.post("/webhook/whatsapp", data={"From": "whatsapp:+919876543210"})
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_webhook_missing_from_returns_ok(client: TestClient):
    """Webhook should ignore malformed payloads with missing sender."""
    response = client.post("/webhook/whatsapp", data={"Body": "Hi, I want to order a cake"})
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_webhook_invalid_signature_rejected(client: TestClient):
    """Webhook must reject payloads without Twilio signature when validation is enabled."""
    response = client.post(
        "/webhook/whatsapp",
        data={"From": "whatsapp:+919876543210", "Body": "Hello"},
    )
    assert response.status_code == 403
