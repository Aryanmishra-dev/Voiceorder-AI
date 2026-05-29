"""Twilio webhook validation and WhatsApp messaging."""

from fastapi import Request
from twilio.rest import Client as TwilioClient

from app.core.config import settings
from app.core.logging import get_logger
from app.core.security import mask_identifier, validate_twilio_webhook as validate_signature

logger = get_logger(__name__)

twilio_client = TwilioClient(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)


async def validate_twilio_webhook(request: Request, url: str, params: dict) -> bool:
    """Validate incoming Twilio webhook signature."""
    return await validate_signature(request, url, params)


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
