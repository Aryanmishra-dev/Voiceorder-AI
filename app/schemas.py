"""Pydantic schemas for request/response validation."""
from pydantic import BaseModel, Field, validator
from datetime import datetime
from typing import Optional
from uuid import UUID


class OrderResponse(BaseModel):
    """Schema for order API response."""
    id: UUID
    phone: str
    customer_name: Optional[str] = None
    cake_type: Optional[str] = None
    flavour: Optional[str] = None
    size_kg: Optional[str] = None
    delivery_date: Optional[str] = None
    delivery_address: Optional[str] = None
    special_notes: Optional[str] = None
    status: str = "new"
    created_at: datetime
    
    class Config:
        from_attributes = True


class OrderStatusUpdate(BaseModel):
    """Schema for updating order status."""
    status: str = Field(..., min_length=1, max_length=50)
    
    @validator('status')
    def status_must_be_valid(cls, v):
        valid_statuses = ['new', 'confirmed', 'in_progress', 'completed', 'cancelled']
        if v.lower() not in valid_statuses:
            raise ValueError(f'Status must be one of {valid_statuses}')
        return v.lower()


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
