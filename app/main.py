"""FastAPI application for WhatsApp cake ordering bot."""
from fastapi import FastAPI, Request, Depends, Form, Response, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func
from contextlib import asynccontextmanager
from twilio.rest import Client as TwilioClient
from datetime import datetime
import json
from math import ceil

from app.config import settings
from app.database import engine, Base, get_db
from app.models import Conversation, Order
from app.bot import chat, extract_order
from app.security import validate_twilio_webhook, check_rate_limit, rate_limiter
from app.schemas import (
    OrderResponse, OrderStatusUpdate, ErrorResponse,
    HealthResponse, PaginatedOrdersResponse
)
from app.logger import get_logger
from app.types import Message

logger = get_logger(__name__)

# ── Startup: create tables ─────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown."""
    logger.info("Starting up application...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created/verified")
    yield
    logger.info("Shutting down application...")
    rate_limiter.cleanup_old_entries()

app = FastAPI(
    title="Sweet Moments WhatsApp Cake Bot",
    description="AI-powered WhatsApp bot for cake ordering",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

templates = Jinja2Templates(directory="app/templates")

twilio_client = TwilioClient(
    settings.TWILIO_ACCOUNT_SID,
    settings.TWILIO_AUTH_TOKEN
)


# ── Helper: send WhatsApp message via Twilio ───────────────────
def send_whatsapp(to: str, body: str) -> bool:
    """Send a WhatsApp message via Twilio.
    
    Args:
        to: WhatsApp number (e.g., whatsapp:+919876543210)
        body: Message text
    
    Returns:
        True if successful, False otherwise
    """
    try:
        twilio_client.messages.create(
            from_=settings.TWILIO_WHATSAPP_NUMBER,
            to=to,
            body=body
        )
        logger.info(f"WhatsApp message sent to {to}")
        return True
    except Exception as e:
        logger.error(f"Failed to send WhatsApp message to {to}: {e}", exc_info=True)
        return False


# ── Webhook: Twilio posts here on every incoming message ───────
@app.post("/webhook/whatsapp")
async def whatsapp_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Handle incoming WhatsApp messages from Twilio webhook.
    
    Returns:
        200 OK response (required by Twilio)
    """
    try:
        form = await request.form()
        incoming_msg = form.get("Body", "").strip()
        from_number = form.get("From", "")  # e.g. whatsapp:+919876543210
        
        if not incoming_msg or not from_number:
            logger.warning(f"Invalid webhook payload: missing Body or From")
            return JSONResponse({"status": "ok"}, status_code=200)
        
        # Validate webhook signature
        is_valid = await validate_twilio_webhook(request, str(request.url), dict(form))
        if not is_valid:
            logger.error(f"Invalid webhook signature from {from_number}")
            raise HTTPException(status_code=403, detail="Invalid signature")
        
        # Check rate limit
        try:
            check_rate_limit(from_number)
        except HTTPException as e:
            logger.warning(f"Rate limit exceeded for {from_number}")
            send_whatsapp(from_number, "⏳ Too many messages. Please wait a moment before sending another message.")
            return JSONResponse({"status": "ok"}, status_code=200)
        
        logger.info(f"Processing message from {from_number}: '{incoming_msg[:50]}...'")
        
        # Load or create conversation
        result = await db.execute(
            select(Conversation).where(Conversation.phone == from_number)
        )
        convo = result.scalar_one_or_none()
        
        if convo is None:
            convo = Conversation(phone=from_number, history=[])
            db.add(convo)
            logger.info(f"Created new conversation for {from_number}")
        
        history: list[Message] = list(convo.history or [])
        
        # Get bot reply with error handling
        try:
            reply, order_complete = await chat(history, incoming_msg)
        except Exception as e:
            logger.error(f"Chat error for {from_number}: {e}", exc_info=True)
            reply = "🔧 I encountered a technical issue. Please try again in a moment."
            order_complete = False
        
        # Save updated history
        convo.history = history
        await db.flush()
        
        # If order complete: extract + save
        if order_complete:
            try:
                order_data = await extract_order(history)
                logger.debug(f"Extracted order data: {order_data}")
                
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
                logger.info(f"Order created for {from_number}")
                
                # Reset conversation so customer can order again
                convo.history = []
            except Exception as e:
                logger.error(f"Failed to extract/save order for {from_number}: {e}", exc_info=True)
                reply += "\n⚠️ There was an issue saving your order. Please contact support."
        
        await db.commit()
        
        # Send reply back via Twilio
        send_whatsapp(from_number, reply)
        
        return JSONResponse({"status": "ok"}, status_code=200)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unhandled error in webhook: {e}", exc_info=True)
        return JSONResponse({"status": "error"}, status_code=500)


# ── Dashboard: shopkeeper view ─────────────────────────────────
@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, db: AsyncSession = Depends(get_db)):
    """Render the order dashboard."""
    try:
        result = await db.execute(
            select(Order).order_by(desc(Order.created_at))
        )
        orders = result.scalars().all()
        return templates.TemplateResponse(
            "dashboard.html",
            {"request": request, "orders": orders}
        )
    except Exception as e:
        logger.error(f"Error loading dashboard: {e}", exc_info=True)
        return templates.TemplateResponse(
            "dashboard.html",
            {"request": request, "orders": [], "error": "Failed to load orders"}
        )


# ── Paginated Orders API ───────────────────────────────────────
@app.get("/api/v1/orders", response_model=PaginatedOrdersResponse)
async def get_orders(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = Query(None),
    db: AsyncSession = Depends(get_db)
) -> PaginatedOrdersResponse:
    """Get paginated list of orders (API endpoint).
    
    Args:
        page: Page number (1-indexed)
        page_size: Number of items per page (1-100)
        status: Filter by status (optional)
    
    Returns:
        Paginated orders response
    """
    try:
        # Build query
        query = select(Order)
        if status:
            query = query.where(Order.status == status.lower())
        
        # Get total count
        count_result = await db.execute(select(func.count()).select_from(Order))
        total = count_result.scalar() or 0
        
        # Apply pagination
        offset = (page - 1) * page_size
        query = query.order_by(desc(Order.created_at)).offset(offset).limit(page_size)
        
        result = await db.execute(query)
        orders = result.scalars().all()
        
        logger.info(f"Fetched page {page} with {len(orders)} orders")
        
        total_pages = ceil(total / page_size) if total > 0 else 1
        
        return PaginatedOrdersResponse(
            orders=[OrderResponse.from_orm(order) for order in orders],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )
    except Exception as e:
        logger.error(f"Error fetching orders: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch orders")


# ── Update Order Status ────────────────────────────────────────
@app.post("/api/v1/order/{order_id}/status", response_model=dict)
async def update_order_status(
    order_id: str,
    status_update: OrderStatusUpdate,
    db: AsyncSession = Depends(get_db)
) -> dict:
    """Update order status.
    
    Args:
        order_id: Order UUID
        status_update: New status
    
    Returns:
        Updated order data
    """
    try:
        result = await db.execute(select(Order).where(Order.id == order_id))
        order = result.scalar_one_or_none()
        
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        
        old_status = order.status
        order.status = status_update.status
        await db.commit()
        await db.refresh(order)
        
        logger.info(f"Order {order_id} status updated: {old_status} -> {order.status}")
        
        return {
            "id": str(order.id),
            "status": order.status,
            "updated_at": datetime.utcnow().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating order {order_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to update order status")


# ── Update Order Status (HTMX endpoint) ────────────────────────
@app.post("/order/{order_id}/status")
async def update_order_status_htmx(
    order_id: str,
    status: str = Form(...),
    db: AsyncSession = Depends(get_db)
):
    """HTMX endpoint for updating order status from dashboard."""
    try:
        result = await db.execute(select(Order).where(Order.id == order_id))
        order = result.scalar_one_or_none()
        
        if order:
            order.status = status
            await db.commit()
            logger.info(f"Order {order_id} status updated to {status} via HTMX")
        
        response = Response()
        response.headers["HX-Trigger"] = "orderStatusChanged"
        return response
    except Exception as e:
        logger.error(f"Error updating order status via HTMX: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to update status")


# ── Health check ───────────────────────────────────────────────
@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Health check endpoint."""
    logger.debug("Health check called")
    return HealthResponse(
        status="ok",
        timestamp=datetime.utcnow()
    )


# ── Error handlers ─────────────────────────────────────────────
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions with proper logging."""
    logger.warning(f"HTTP {exc.status_code}: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error=f"HTTP {exc.status_code}",
            detail=exc.detail,
            status_code=exc.status_code
        ).dict()
    )

