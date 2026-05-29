"""Order API routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db, require_admin
from app.core.logging import get_logger
from app.schemas.order import OrderStatusUpdate, PaginatedOrdersResponse
from app.services.order_service import list_orders, status_update_payload, update_order_status

logger = get_logger(__name__)
router = APIRouter()


@router.get("/api/v1/orders", response_model=PaginatedOrdersResponse)
async def get_orders(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = Query(None, max_length=20),
    db: AsyncSession = Depends(get_db),
    _admin: None = Depends(require_admin),
) -> PaginatedOrdersResponse:
    """Get paginated list of orders."""
    try:
        return await list_orders(db, page=page, page_size=page_size, status=status)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Error fetching orders: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch orders")


@router.post("/api/v1/order/{order_id}/status", response_model=dict)
async def update_order_status_api(
    order_id: UUID,
    status_update: OrderStatusUpdate,
    db: AsyncSession = Depends(get_db),
    _admin: None = Depends(require_admin),
) -> dict:
    """Update order status from JSON API."""
    try:
        order = await update_order_status(db, order_id, status_update.status)
        return status_update_payload(order)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Error updating order %s: %s", order_id, exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to update order status")
