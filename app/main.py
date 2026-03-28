from fastapi import FastAPI, Request, Depends, Form, Response
from fastapi.responses import HTMLResponse, PlainTextResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from contextlib import asynccontextmanager
from twilio.rest import Client as TwilioClient
import json

from app.config import settings
from app.database import engine, Base, get_db
from app.models import Conversation, Order
from app.bot import chat, extract_order

# ── Startup: create tables ─────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield

app = FastAPI(title="Cake Shop WhatsApp Bot", lifespan=lifespan)
templates = Jinja2Templates(directory="app/templates")

twilio_client = TwilioClient(
    settings.TWILIO_ACCOUNT_SID,
    settings.TWILIO_AUTH_TOKEN
)


# ── Helper: send WhatsApp message via Twilio ───────────────────
def send_whatsapp(to: str, body: str):
    twilio_client.messages.create(
        from_=settings.TWILIO_WHATSAPP_NUMBER,
        to=to,
        body=body
    )


# ── Webhook: Twilio posts here on every incoming message ───────
@app.post("/webhook/whatsapp")
async def whatsapp_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    form = await request.form()
    incoming_msg = form.get("Body", "").strip()
    from_number  = form.get("From", "")   # e.g. whatsapp:+919876543210

    if not incoming_msg or not from_number:
        return PlainTextResponse("ok")

    # ── Load or create conversation ────────────────────────────
    result = await db.execute(
        select(Conversation).where(Conversation.phone == from_number)
    )
    convo = result.scalar_one_or_none()

    if convo is None:
        convo = Conversation(phone=from_number, history=[])
        db.add(convo)

    history = list(convo.history or [])

    # ── Get bot reply ──────────────────────────────────────────
    reply, order_complete = await chat(history, incoming_msg)

    # Save updated history
    convo.history = history
    await db.flush()

    # ── If order complete: extract + save ──────────────────────
    if order_complete:
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

        # Reset conversation so customer can order again
        convo.history = []

    await db.commit()

    # ── Send reply back via Twilio ─────────────────────────────
    send_whatsapp(from_number, reply)

    # Twilio expects a 200 with empty or TwiML body
    return PlainTextResponse("ok")


# ── Dashboard: shopkeeper view ─────────────────────────────────
@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Order).order_by(desc(Order.created_at))
    )
    orders = result.scalars().all()
    return templates.TemplateResponse(
        "dashboard.html",
        {"request": request, "orders": orders}
    )

@app.post("/order/{order_id}/status")
async def update_order_status(
    order_id: str,
    status: str = Form(...),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    if order:
        order.status = status
        await db.commit()
    
    response = Response()
    response.headers["HX-Trigger"] = "orderStatusChanged"
    return response


# ── Health check ───────────────────────────────────────────────
@app.get("/health")
async def health():
    return {"status": "ok"}
