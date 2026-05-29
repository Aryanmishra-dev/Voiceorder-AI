"""Twilio WhatsApp webhook routes."""

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db
from app.core.config import settings
from app.core.logging import get_logger
from app.core.security import check_rate_limit, mask_identifier
from app.services.bot_service import process_customer_message
from app.services.twilio_service import send_whatsapp, validate_twilio_webhook

logger = get_logger(__name__)
router = APIRouter()


def _message_log_value(message: str) -> str:
    """Return a safe message log value based on LOG_PII setting."""
    if settings.LOG_PII:
        return message[:50]
    return f"{len(message)} chars"


@router.post("/webhook/whatsapp")
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
        reply = await process_customer_message(db, from_number, incoming_msg)
        send_whatsapp(from_number, reply)
        return JSONResponse({"status": "ok"}, status_code=200)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Unhandled error in webhook: %s", exc, exc_info=True)
        return JSONResponse({"status": "error"}, status_code=500)
