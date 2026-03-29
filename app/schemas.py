"""Pydantic schemas for request/response validation."""
from enum import Enum
from pydantic import ConfigDict
from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from typing import Optional
from uuid import UUID


class OrderStatus(str, Enum):
    """Allowed order statuses."""

    new = "new"
    confirmed = "confirmed"
    in_progress = "in_progress"
    completed = "completed"
    cancelled = "cancelled"


class OrderResponse(BaseModel):
    """Schema for order API response."""
    id: UUID
    phone: str
    customer_name: Optional[str] = None
    cake_type: Optional[str] = None
    flavour: Optional[str] = None
    size_kg: Optional[float] = None
    delivery_date: Optional[str] = None
    delivery_address: Optional[str] = None
    special_notes: Optional[str] = None
    status: OrderStatus = OrderStatus.new
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OrderStatusUpdate(BaseModel):
    """Schema for updating order status."""
    status: OrderStatus = Field(...)

    @field_validator("status", mode="before")
    @classmethod
    def normalize_status(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip().lower()
        return value


class ErrorResponse(BaseModel):
    """Schema for error responses."""
    error: str
    detail: str
    status_code: int


class HealthResponse(BaseModel):
    """Schema for health check response."""
    status: str
    timestamp: datetime


class PaginatedOrdersResponse(BaseModel):
    """Schema for paginated orders response."""
    orders: list[OrderResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
