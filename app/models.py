"""SQLAlchemy ORM models for the application."""
from sqlalchemy import Column, String, Text, DateTime, JSON, Float, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid
from app.database import Base


class Conversation(Base):
    """Stores ongoing chat conversation per WhatsApp number."""
    __tablename__ = "conversations"
    
    # Indexes
    __table_args__ = (
        Index('idx_conversations_phone', 'phone'),
        Index('idx_conversations_updated_at', 'updated_at'),
    )
    
    phone = Column(String(30), primary_key=True)  # whatsapp:+919876543210
    history = Column(JSON, default=list, nullable=False)  # list of {role, content}
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=False)


class Order(Base):
    """Stores completed orders extracted from conversations."""
    __tablename__ = "orders"
    
    # Indexes for common queries
    __table_args__ = (
        Index('idx_orders_phone', 'phone'),
        Index('idx_orders_status', 'status'),
        Index('idx_orders_created_at', 'created_at'),
        Index('idx_orders_customer_name', 'customer_name'),
    )
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    phone = Column(String(30), nullable=False)
    customer_name = Column(String(100), nullable=True)
    cake_type = Column(String(100), nullable=True)
    flavour = Column(String(100), nullable=True)
    size_kg = Column(Float, nullable=True)  # Changed from String to Float for validation
    delivery_date = Column(String(50), nullable=True)
    delivery_address = Column(Text, nullable=True)
    special_notes = Column(Text, nullable=True)
    full_transcript = Column(Text, nullable=True)  # Full conversation for audit trail
    status = Column(String(20), default="new", nullable=False)  # new, confirmed, in_progress, completed, cancelled
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=False)
    
    def __repr__(self) -> str:
        return f"<Order {self.id} - {self.customer_name} - {self.status}>"

