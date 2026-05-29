"""Dashboard routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, Form, HTTPException, Request, Response
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db, require_admin
from app.core.logging import get_logger
from app.models.order import Order
from app.services.order_service import normalize_status, update_order_status

logger = get_logger(__name__)
router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    db: AsyncSession = Depends(get_db),
    _admin: None = Depends(require_admin),
):
    """Render the protected order dashboard."""
    try:
        result = await db.execute(select(Order).order_by(desc(Order.created_at)))
        orders = result.scalars().all()
        return templates.TemplateResponse(request, "dashboard.html", {"request": request, "orders": orders})
    except Exception as exc:
        logger.error("Error loading dashboard: %s", exc, exc_info=True)
        return templates.TemplateResponse(
            request,
            "dashboard.html",
            {"request": request, "orders": [], "error": "Failed to load orders"},
        )


@router.post("/order/{order_id}/status")
async def update_order_status_htmx(
    order_id: UUID,
    status: str = Form(...),
    db: AsyncSession = Depends(get_db),
    _admin: None = Depends(require_admin),
):
    """HTMX endpoint for updating order status from dashboard."""
    try:
        normalized_status = normalize_status(status)
        await update_order_status(db, order_id, normalized_status)
        logger.info("Order %s status updated to %s via HTMX", order_id, normalized_status)

        response = Response()
        response.headers["HX-Trigger"] = "orderStatusChanged"
        return response
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Error updating order status via HTMX: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to update status")
