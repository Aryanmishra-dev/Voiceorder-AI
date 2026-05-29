"""Order CRUD and status management."""

from datetime import datetime, timezone
from math import ceil
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.order import Order
from app.schemas.order import OrderResponse, OrderStatus, PaginatedOrdersResponse
from app.types.domain import OrderData

logger = get_logger(__name__)

ORDER_STATUSES = {status.value for status in OrderStatus}


def normalize_status(value: str) -> str:
    """Normalize and validate incoming order status values."""
    normalized = (value or "").strip().lower()
    if normalized not in ORDER_STATUSES:
        raise HTTPException(
            status_code=422,
            detail=f"Status must be one of {sorted(ORDER_STATUSES)}",
        )
    return normalized


def create_order_from_data(
    db: AsyncSession,
    phone: str,
    order_data: OrderData,
    full_transcript: str,
) -> Order:
    """Create an order ORM object from extracted LLM order data."""
    order = Order(
        phone=phone,
        customer_name=order_data.get("customer_name"),
        cake_type=order_data.get("cake_type"),
        flavour=order_data.get("flavour"),
        size_kg=order_data.get("size_kg"),
        delivery_date=order_data.get("delivery_date"),
        delivery_address=order_data.get("delivery_address"),
        special_notes=order_data.get("special_notes"),
        full_transcript=full_transcript,
    )
    db.add(order)
    return order


async def list_orders(
    db: AsyncSession,
    page: int,
    page_size: int,
    status: str | None = None,
) -> PaginatedOrdersResponse:
    """Get paginated list of orders."""
    normalized_status = normalize_status(status) if status is not None else None

    query = select(Order)
    count_query = select(func.count()).select_from(Order)
    if normalized_status is not None:
        query = query.where(Order.status == normalized_status)
        count_query = count_query.where(Order.status == normalized_status)

    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    offset = (page - 1) * page_size
    query = query.order_by(desc(Order.created_at)).offset(offset).limit(page_size)
    result = await db.execute(query)
    orders = result.scalars().all()

    total_pages = ceil(total / page_size) if total > 0 else 1

    return PaginatedOrdersResponse(
        orders=[OrderResponse.model_validate(order) for order in orders],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


async def update_order_status(db: AsyncSession, order_id: UUID, status: str) -> Order:
    """Update order status and return the refreshed order."""
    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    old_status = order.status
    order.status = status
    await db.commit()
    await db.refresh(order)

    logger.info("Order %s status updated: %s -> %s", order_id, old_status, order.status)
    return order


def status_update_payload(order: Order) -> dict:
    """Build the JSON API response payload for status updates."""
    return {
        "id": str(order.id),
        "status": order.status,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
