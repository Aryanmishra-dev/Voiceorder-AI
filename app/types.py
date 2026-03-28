"""Type definitions for the application."""
from typing import TypedDict, NotRequired


class Message(TypedDict):
    """Message format in conversation history."""
    role: str  # "user" or "assistant"
    content: str


class OrderData(TypedDict):
    """Extracted order data structure."""
    customer_name: NotRequired[str | None]
    cake_type: NotRequired[str | None]
    flavour: NotRequired[str | None]
    size_kg: NotRequired[str | None]
    delivery_date: NotRequired[str | None]
    delivery_address: NotRequired[str | None]
    special_notes: NotRequired[str | None]


class WebhookPayload(TypedDict):
    """Twilio webhook payload."""
    Body: str
    From: str
    AccountSid: str
    MessageSid: str
    NumMedia: str
