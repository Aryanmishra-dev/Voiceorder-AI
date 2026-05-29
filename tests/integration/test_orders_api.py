"""Tests for order API routes."""

from fastapi.testclient import TestClient


def test_orders_api_requires_auth(client: TestClient):
    """Orders API should be protected."""
    response = client.get("/api/v1/orders")
    assert response.status_code == 401


def test_orders_pagination_defaults(client: TestClient, auth_headers: dict[str, str]):
    """Orders endpoint returns pagination metadata for authenticated requests."""
    response = client.get("/api/v1/orders", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["orders"] == []
    assert data["total"] == 0
    assert data["page"] == 1
    assert data["page_size"] == 20


def test_orders_pagination_custom(client: TestClient, auth_headers: dict[str, str]):
    """Orders endpoint accepts custom pagination params."""
    response = client.get("/api/v1/orders?page=2&page_size=10", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["page"] == 2
    assert data["page_size"] == 10


def test_orders_pagination_invalid_page(client: TestClient, auth_headers: dict[str, str]):
    """Orders endpoint should reject invalid page numbers."""
    response = client.get("/api/v1/orders?page=0", headers=auth_headers)
    assert response.status_code == 422


def test_orders_pagination_max_page_size(client: TestClient, auth_headers: dict[str, str]):
    """Orders endpoint should enforce max page size limit."""
    response = client.get("/api/v1/orders?page_size=1000", headers=auth_headers)
    assert response.status_code == 422


def test_update_order_status_requires_auth(client: TestClient):
    """Order status API should reject anonymous update attempts."""
    response = client.post(
        "/api/v1/order/00000000-0000-0000-0000-000000000000/status",
        json={"status": "confirmed"},
    )
    assert response.status_code == 401


def test_invalid_order_status_rejected(client: TestClient, auth_headers: dict[str, str]):
    """Order status validation should reject unknown values."""
    response = client.post(
        "/api/v1/order/00000000-0000-0000-0000-000000000000/status",
        json={"status": "invalid_status"},
        headers=auth_headers,
    )
    assert response.status_code == 422
