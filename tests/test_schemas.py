"""Tests for Pydantic schemas."""
import pytest
from app.schemas import OrderStatusUpdate, OrderResponse, PaginatedOrdersResponse
from datetime import datetime
from uuid import uuid4


def test_order_status_update_valid():
    """Test OrderStatusUpdate with valid status."""
    update = OrderStatusUpdate(status="confirmed")
    assert update.status == "confirmed"


def test_order_status_update_case_insensitive():
    """Test that status is converted to lowercase."""
    update = OrderStatusUpdate(status="CONFIRMED")
    assert update.status == "confirmed"


def test_order_status_update_invalid():
    """Test OrderStatusUpdate rejects invalid status."""
    with pytest.raises(ValueError):
        OrderStatusUpdate(status="invalid_status")


def test_order_status_update_valid_statuses():
    """Test all valid statuses are accepted."""
    valid_statuses = ['new', 'confirmed', 'in_progress', 'completed', 'cancelled']
    
    for status in valid_statuses:
        update = OrderStatusUpdate(status=status)
        assert update.status == status


def test_paginated_orders_response():
    """Test PaginatedOrdersResponse schema."""
    response = PaginatedOrdersResponse(
        orders=[],
        total=0,
        page=1,
        page_size=20,
        total_pages=1
    )
    assert response.total == 0
    assert response.page == 1
    assert response.total_pages == 1


def test_order_response_from_orm():
    """Test OrderResponse can be created from ORM object."""
    from sqlalchemy.orm import declarative_base
    from sqlalchemy import Column, String, UUID
    import uuid
    
    # Create a mock Order object
    class MockOrder:
        id = uuid.uuid4()
        phone = "whatsapp:+919876543210"
        customer_name = "John Doe"
        cake_type = "Chocolate"
        flavour = "vanilla"
        size_kg = "1.0"
        delivery_date = "2024-04-01"
        delivery_address = "123 Main St"
        special_notes = "Write Happy Birthday"
        status = "new"
        created_at = datetime.utcnow()
    
    # Should not raise
    response = OrderResponse.from_orm(MockOrder())
    assert response.customer_name == "John Doe"
    assert response.status == "new"
