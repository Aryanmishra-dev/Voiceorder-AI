"""Conversation orchestration for WhatsApp order intake."""

import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.security import mask_identifier
from app.models.order import Conversation
from app.services.llm_service import chat, extract_order
from app.services.order_service import create_order_from_data
from app.types.domain import Message

logger = get_logger(__name__)


async def process_customer_message(db: AsyncSession, from_number: str, incoming_msg: str) -> str:
    """Process a customer message and return the WhatsApp reply text."""
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
            create_order_from_data(
                db=db,
                phone=from_number,
                order_data=order_data,
                full_transcript=json.dumps(history, ensure_ascii=False),
            )
            convo.history = []
            logger.info("Order created for %s", mask_identifier(from_number))
        except Exception as exc:
            logger.error("Failed to extract/save order for %s: %s", mask_identifier(from_number), exc, exc_info=True)
            reply += "\nThere was an issue saving your order. Please contact support."

    await db.commit()
    return reply
