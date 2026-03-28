"""Tests for the main FastAPI application."""
import pytest
from fastapi.testclient import TestClient
from app.main import app


def test_health_check():
    """Test the health check endpoint."""
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "timestamp" in data


def test_health_check_response_format():
    """Test health check response has correct format."""
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"


@pytest.mark.asyncio
async def test_webhook_missing_body():
    """Test webhook with missing Body parameter."""
    client = TestClient(app)
    response = client.post(
        "/webhook/whatsapp",
        data={"From": "whatsapp:+919876543210"}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_webhook_missing_from():
    """Test webhook with missing From parameter."""
    client = TestClient(app)
    response = client.post(
        "/webhook/whatsapp",
        data={"Body": "Hi, I want to order a cake"}
    )
    assert response.status_code == 200


def test_invalid_order_status():
    """Test updating order with invalid status."""
    client = TestClient(app)
    # This will fail because order doesn't exist, but tests validation
    response = client.post(
        "/api/v1/order/00000000-0000-0000-0000-000000000000/status",
        json={"status": "invalid_status"}
    )
    # Either 404 (not found) or 422 (validation error) is acceptable
    assert response.status_code in [404, 422]


def test_orders_pagination_defaults():
    """Test orders endpoint with default pagination."""
    client = TestClient(app)
    response = client.get("/api/v1/orders")
    assert response.status_code == 200
    data = response.json()
    assert "orders" in data
    assert "total" in data
    assert "page" in data
    assert data["page"] == 1


def test_orders_pagination_custom():
    """Test orders endpoint with custom pagination parameters."""
    client = TestClient(app)
    response = client.get("/api/v1/orders?page=2&page_size=10")
    assert response.status_code == 200
    data = response.json()
    assert data["page"] == 2
    assert data["page_size"] == 10


def test_orders_pagination_invalid_page():
    """Test orders endpoint with invalid page number."""
    client = TestClient(app)
    response = client.get("/api/v1/orders?page=0")
    assert response.status_code == 422  # Validation error


def test_orders_pagination_max_page_size():
    """Test orders endpoint respects max page size."""
    client = TestClient(app)
    response = client.get("/api/v1/orders?page_size=1000")
    assert response.status_code == 422  # Should be rejected, max is 100
