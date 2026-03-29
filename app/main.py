"""FastAPI application for WhatsApp cake ordering bot."""

import json
import secrets
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from math import ceil
from uuid import UUID

from fastapi import Depends, FastAPI, Form, HTTPException, Query, Request, Response, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.security import APIKeyHeader, HTTPBasic, HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.middleware.trustedhost import TrustedHostMiddleware
from twilio.rest import Client as TwilioClient

from app.bot import chat, extract_order
from app.config import settings
from app.database import Base, engine, get_db
from app.logger import get_logger
from app.models import Conversation, Order
from app.schemas import ErrorResponse, HealthResponse, OrderResponse, OrderStatus, OrderStatusUpdate, PaginatedOrdersResponse
from app.security import check_rate_limit, mask_identifier, rate_limiter, validate_twilio_webhook
from app.types import Message

logger = get_logger(__name__)

ORDER_STATUSES = {status.value for status in OrderStatus}

admin_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
admin_basic_auth = HTTPBasic(auto_error=False)


def _safe_compare(left: str, right: str) -> bool:
    """Constant-time compare wrapper."""
    return secrets.compare_digest(left.encode("utf-8"), right.encode("utf-8"))


async def require_admin(
    api_key: str | None = Security(admin_api_key_header),
    credentials: HTTPBasicCredentials | None = Security(admin_basic_auth),
) -> None:
    """Protect admin routes using API key or HTTP basic auth."""
    if api_key and _safe_compare(api_key, settings.ADMIN_API_KEY):
        return

    if credentials:
        if _safe_compare(credentials.username, settings.ADMIN_USERNAME) and _safe_compare(
            credentials.password, settings.ADMIN_PASSWORD
        ):
            return

    raise HTTPException(
        status_code=401,
        detail="Authentication required",
        headers={"WWW-Authenticate": 'Basic realm="AI BOT SERVICE Dashboard"'},
    )


def normalize_status(value: str) -> str:
    """Normalize and validate incoming order status values."""
    normalized = (value or "").strip().lower()
    if normalized not in ORDER_STATUSES:
        raise HTTPException(
            status_code=422,
            detail=f"Status must be one of {sorted(ORDER_STATUSES)}",
        )
    return normalized


def _message_log_value(message: str) -> str:
    """Return a safe message log value based on LOG_PII setting."""
    if settings.LOG_PII:
        return message[:50]
    return f"{len(message)} chars"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown."""
    logger.info("Starting up application")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created/verified")
    yield
    logger.info("Shutting down application")
    rate_limiter.cleanup_old_entries()


app = FastAPI(
    title="AI BOT SERVICE",
    description="AI-powered WhatsApp bot for cake ordering",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.trusted_hosts)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type", "X-API-Key"],
)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """Apply baseline security headers to all responses."""
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
    response.headers.setdefault("Cross-Origin-Opener-Policy", "same-origin")
    response.headers.setdefault("Cross-Origin-Resource-Policy", "same-origin")
    response.headers.setdefault(
        "Content-Security-Policy",
        "default-src 'self'; "
        "script-src 'self' https://unpkg.com; "
        "style-src 'self' https://fonts.googleapis.com 'unsafe-inline'; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' data:; "
        "connect-src 'self'; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self'",
    )
    if settings.ENABLE_HSTS:
        response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
    return response


app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

twilio_client = TwilioClient(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)


def send_whatsapp(to: str, body: str) -> bool:
    """Send a WhatsApp message via Twilio."""
    try:
        twilio_client.messages.create(
            from_=settings.TWILIO_WHATSAPP_NUMBER,
            to=to,
            body=body,
        )
        logger.info("WhatsApp message sent to %s", mask_identifier(to))
        return True
    except Exception as exc:
        logger.error("Failed to send WhatsApp message to %s: %s", mask_identifier(to), exc, exc_info=True)
        return False


@app.post("/webhook/whatsapp")
async def whatsapp_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """Handle incoming WhatsApp messages from Twilio webhook."""
    try:
        form = await request.form()
        incoming_msg = form.get("Body", "").strip()
        from_number = form.get("From", "").strip()

        if not incoming_msg or not from_number:
            logger.warning("Invalid webhook payload: missing Body or From")
            return JSONResponse({"status": "ok"}, status_code=200)

        is_valid = await validate_twilio_webhook(request, str(request.url), dict(form))
        if not is_valid:
            logger.error("Invalid webhook signature from %s", mask_identifier(from_number))
            raise HTTPException(status_code=403, detail="Invalid signature")

        try:
            check_rate_limit(from_number)
        except HTTPException:
            logger.warning("Rate limit exceeded for %s", mask_identifier(from_number))
            send_whatsapp(from_number, "Too many messages. Please wait and try again.")
            return JSONResponse({"status": "ok"}, status_code=200)

        logger.info("Processing message from %s (%s)", mask_identifier(from_number), _message_log_value(incoming_msg))

        result = await db.execute(select(Conversation).where(Conversation.phone == from_number))
        convo = result.scalar_one_or_none()
        if convo is None:
            convo = Conversation(phone=from_number, history=[])
            db.add(convo)
            logger.info("Created new conversation for %s", mask_identifier(from_number))

        history: list[Message] = list(convo.history or [])

        try:
            reply, order_complete = await chat(history, incoming_msg)
        except Exception as exc:
            logger.error("Chat error for %s: %s", mask_identifier(from_number), exc, exc_info=True)
            reply = "I encountered a technical issue. Please try again shortly."
            order_complete = False

        convo.history = history
        await db.flush()

        if order_complete:
            try:
                order_data = await extract_order(history)
                order = Order(
                    phone=from_number,
                    customer_name=order_data.get("customer_name"),
                    cake_type=order_data.get("cake_type"),
                    flavour=order_data.get("flavour"),
                    size_kg=order_data.get("size_kg"),
                    delivery_date=order_data.get("delivery_date"),
                    delivery_address=order_data.get("delivery_address"),
                    special_notes=order_data.get("special_notes"),
                    full_transcript=json.dumps(history, ensure_ascii=False),
                )
                db.add(order)
                convo.history = []
                logger.info("Order created for %s", mask_identifier(from_number))
            except Exception as exc:
                logger.error("Failed to extract/save order for %s: %s", mask_identifier(from_number), exc, exc_info=True)
                reply += "\nThere was an issue saving your order. Please contact support."

        await db.commit()
        send_whatsapp(from_number, reply)
        return JSONResponse({"status": "ok"}, status_code=200)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Unhandled error in webhook: %s", exc, exc_info=True)
        return JSONResponse({"status": "error"}, status_code=500)


@app.get("/dashboard", response_class=HTMLResponse)
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


@app.get("/api/v1/orders", response_model=PaginatedOrdersResponse)
async def get_orders(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = Query(None, max_length=20),
    db: AsyncSession = Depends(get_db),
    _admin: None = Depends(require_admin),
) -> PaginatedOrdersResponse:
    """Get paginated list of orders."""
    try:
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
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Error fetching orders: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch orders")


@app.post("/api/v1/order/{order_id}/status", response_model=dict)
async def update_order_status(
    order_id: UUID,
    status_update: OrderStatusUpdate,
    db: AsyncSession = Depends(get_db),
    _admin: None = Depends(require_admin),
) -> dict:
    """Update order status from JSON API."""
    try:
        result = await db.execute(select(Order).where(Order.id == order_id))
        order = result.scalar_one_or_none()
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")

        old_status = order.status
        order.status = status_update.status
        await db.commit()
        await db.refresh(order)

        logger.info("Order %s status updated: %s -> %s", order_id, old_status, order.status)
        return {
            "id": str(order.id),
            "status": order.status,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Error updating order %s: %s", order_id, exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to update order status")


@app.post("/order/{order_id}/status")
async def update_order_status_htmx(
    order_id: UUID,
    status: str = Form(...),
    db: AsyncSession = Depends(get_db),
    _admin: None = Depends(require_admin),
):
    """HTMX endpoint for updating order status from dashboard."""
    try:
        normalized_status = normalize_status(status)
        result = await db.execute(select(Order).where(Order.id == order_id))
        order = result.scalar_one_or_none()
        if order is None:
            raise HTTPException(status_code=404, detail="Order not found")

        order.status = normalized_status
        await db.commit()
        logger.info("Order %s status updated to %s via HTMX", order_id, normalized_status)

        response = Response()
        response.headers["HX-Trigger"] = "orderStatusChanged"
        return response
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Error updating order status via HTMX: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to update status")


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Health check endpoint."""
    return HealthResponse(status="ok", timestamp=datetime.now(timezone.utc))


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions with structured JSON output."""
    logger.warning("HTTP %s: %s", exc.status_code, exc.detail)
    detail = exc.detail if isinstance(exc.detail, str) else json.dumps(exc.detail, ensure_ascii=False)
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error=f"HTTP {exc.status_code}",
            detail=detail,
            status_code=exc.status_code,
        ).model_dump(),
        headers=exc.headers,
    )

