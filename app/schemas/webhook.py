"""Twilio webhook request schemas."""

from pydantic import BaseModel


class TwilioWebhookPayload(BaseModel):
    """Subset of Twilio form payload fields used by the webhook."""

    Body: str
    From: str
    AccountSid: str | None = None
    MessageSid: str | None = None
    NumMedia: str | None = None
