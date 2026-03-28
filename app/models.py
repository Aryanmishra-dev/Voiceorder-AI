from sqlalchemy import Column, String, Text, DateTime, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid
from app.database import Base


class Conversation(Base):
    """Tracks the ongoing chat per WhatsApp number."""
    __tablename__ = "conversations"

    phone = Column(String(30), primary_key=True)   # whatsapp:+919876543210
    history = Column(JSON, default=list)            # list of {role, content}
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class Order(Base):
    """A completed order extracted from a conversation."""
    __tablename__ = "orders"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    phone = Column(String(30), nullable=False)
    customer_name = Column(String(100), nullable=True)
    cake_type = Column(String(100), nullable=True)
    flavour = Column(String(100), nullable=True)
    size_kg = Column(String(20), nullable=True)
    delivery_date = Column(String(50), nullable=True)
    delivery_address = Column(Text, nullable=True)
    special_notes = Column(Text, nullable=True)
    full_transcript = Column(Text, nullable=True)
    status = Column(String(20), default="new")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
