"""LLM prompting and extraction for cake order conversations."""
from openai import AsyncOpenAI, APIError, APITimeoutError
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)
import json
import re

from app.core.config import settings
from app.core.logging import get_logger
from app.types.domain import Message, OrderData

logger = get_logger(__name__)

client = AsyncOpenAI(
    api_key=settings.OPENAI_API_KEY,
    base_url="https://openrouter.ai/api/v1",
    timeout=settings.LLM_TIMEOUT_SECONDS
)


def is_vague_response(message: str) -> bool:
    """
    Check if user message is too vague (just acknowledgment, not an actual answer).
    
    Args:
        message: User's message
        
    Returns:
        True if message is vague (ok, yeah, fine, etc.), False if substantive
    """
    # Normalize: lowercase, strip whitespace
    clean = message.lower().strip()
    
    # List of vague responses to reject
    vague_patterns = [
        r'^ok\.?$',
        r'^okay\.?$',
        r'^yeah\.?$',
        r'^yep\.?$',
        r'^sure\.?$',
        r'^fine\.?$',
        r'^alright\.?$',
        r'^right\.?$',
        r'^got it\.?$',
        r'^understood\.?$',
        r'^ok then\.?$',
        r'^yes\.?$',
        r'^ya\.?$',
        r'^yup\.?$',
        r'^mhm\.?$',
        r'^hmm\.?$',
        r'^ok got it\.?$',
    ]
    
    for pattern in vague_patterns:
        if re.match(pattern, clean):
            return True
    
    return False

# ── System prompt ──────────────────────────────────────────────
SYSTEM_PROMPT = """
You are a friendly WhatsApp assistant for "AI BOT SERVICE" cake shop.
Your job is to take cake orders from customers over WhatsApp chat.

CONVERSATION FLOW - STRICT SEQUENCE:
1. Greet ONCE (only on first message): "Hello! 😊 I'm so glad you reached out to order a cake. What kind of cake are you looking for?"
2. For EACH subsequent customer response:
   a) Acknowledge their answer briefly: "Got it!", "Perfect!", "Great!", "Ok, understood"
   b) Say what you noted (optional): e.g., "So you want chocolate cake"
   c) Ask the NEXT question IMMEDIATELY in the same message

INFORMATION TO COLLECT (in this exact order):
1. Cake type (chocolate, vanilla, black forest, etc.) → Then ask for customer name
2. Customer name (e.g., "Dadda Tyagi") → Then ask for size
3. Size in kg (0.5kg, 1kg, 2kg) → Then ask for delivery date
4. Delivery date (e.g., "30-04-2026") → Then ask for delivery address
5. Delivery address (e.g., "Sanjana Part 5, Delhi") → Then ask for special notes
6. Special notes (message on cake, dietary needs, etc.) → Then CONFIRM the order

CONFIRMATION:
- Once all details are collected, send a summary with the [ORDER_COMPLETE] tag
- Format: "Perfect! Here's a summary of your order: [list details]. Please confirm if everything is correct!"
- Wait for "confirm" or "yes"
- After they confirm, say "Thank you! The shopkeeper will contact you soon with pricing details." [ORDER_COMPLETE]

RESPONSE STRUCTURE EXAMPLE:
Customer: "Chocolate cake"
Bot: "Perfect! 🎂 Chocolate cake noted. Now, could you tell me your name?"

Customer: "Dadda Tyagi"
Bot: "Great! Thanks, Dadda Tyagi. What size cake would you like? (e.g., 0.5kg, 1kg, 2kg)"

Customer: "1kg"
Bot: "Excellent! 1kg noted. When would you like the cake delivered? (e.g., 30-04-2026)"

RULES:
- Start with acknowledgment ("Got it!", "Perfect!", "Great!", etc.)
- Immediately follow with the next question
- Keep messages short and friendly
- One question per message
- Do NOT ask multiple questions in one message
- If customer provides multiple details, acknowledge and ask for next sequential item
- Do not make up prices
- If customer gives vague response (just "ok"), reject it and ask for real answer

VAGUE RESPONSE HANDLING:
- If customer ONLY says "ok", "yeah", "fine", "yes" without substance, ask for the actual answer
- Example: Customer: "ok" → Bot: "I need a real answer! What kind of cake would you like?"

MESSAGE STRUCTURE (IMPORTANT):
[Acknowledgment] [Noted detail if applicable] [Next Question]

All in ONE message, not separate messages.
"""

EXTRACT_PROMPT = """
You are a data extraction assistant. 
Given the conversation below, extract the order details as JSON.
Return ONLY valid JSON, nothing else.

JSON format:
{
  "customer_name": "...",
  "cake_type": "...",
  "flavour": "...",
  "size_kg": "...",
  "delivery_date": "...",
  "delivery_address": "...",
  "special_notes": "..."
}

Use null for any field not mentioned. 
Conversation:
"""


@retry(
    stop=stop_after_attempt(settings.LLM_MAX_RETRIES),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((APIError, APITimeoutError)),
    reraise=True,
)
async def chat(
    history: list[Message],
    user_message: str
) -> tuple[str, bool]:
    """
    Send user message to LLM, get bot reply.
    
    Args:
        history: List of previous messages in conversation
        user_message: The new user message
    
    Returns:
        Tuple of (reply_text, order_is_complete)
    
    Raises:
        APIError: If OpenRouter API fails after retries
        APITimeoutError: If API call times out after retries
    """
    try:
        # Check if user's response is too vague (just "ok", "yeah", etc.)
        if len(history) > 0 and is_vague_response(user_message):
            logger.warning(f"Detected vague response: '{user_message}'. Asking for clarification.")
            # Don't add vague response to history, instead ask for real answer
            vague_response = (
                "I need a real answer, not just 'ok'! 😊 "
                "Please provide the information I'm asking for. "
                "What's your response?"
            )
            return vague_response, False
        
        history.append({"role": "user", "content": user_message})
        logger.debug(f"Processing message from user, history size: {len(history)}")
        
        response = await client.chat.completions.create(
            model="openai/gpt-4o-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                *history
            ],
            max_tokens=settings.LLM_MAX_TOKENS,
            temperature=settings.LLM_TEMPERATURE,
        )
        
        reply = response.choices[0].message.content.strip()
        history.append({"role": "assistant", "content": reply})
        
        order_complete = "[ORDER_COMPLETE]" in reply
        # Clean the tag from what customer sees
        clean_reply = reply.replace("[ORDER_COMPLETE]", "").strip()
        
        logger.info(
            f"Chat response generated, order_complete={order_complete}, "
            f"reply_length={len(clean_reply)}"
        )
        return clean_reply, order_complete
        
    except APITimeoutError as e:
        logger.error(f"LLM API timeout: {e}", exc_info=True)
        raise
    except APIError as e:
        logger.error(f"LLM API error: {e}", exc_info=True)
        raise
    except Exception as e:
        logger.error(f"Unexpected error in chat: {e}", exc_info=True)
        raise


@retry(
    stop=stop_after_attempt(settings.LLM_MAX_RETRIES),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((APIError, APITimeoutError)),
    reraise=True,
)
async def extract_order(history: list[Message]) -> OrderData:
    """
    Extract structured order data from conversation history.
    
    Args:
        history: Complete conversation history
    
    Returns:
        Dictionary with extracted order details
    
    Raises:
        APIError: If OpenRouter API fails after retries
        json.JSONDecodeError: If response is not valid JSON
    """
    try:
        conversation_text = "\n".join(
            f"{msg['role'].upper()}: {msg['content']}"
            for msg in history
        )
        
        logger.debug(f"Extracting order from {len(history)} messages")
        
        response = await client.chat.completions.create(
            model="openai/gpt-4o-mini",
            messages=[
                {
                    "role": "user",
                    "content": EXTRACT_PROMPT + conversation_text
                }
            ],
            max_tokens=settings.LLM_MAX_TOKENS,
            temperature=settings.LLM_EXTRACTION_TEMPERATURE,
        )
        
        raw = response.choices[0].message.content.strip()
        extracted_data = json.loads(raw)
        
        logger.info(f"Order extraction successful: {extracted_data}")
        return extracted_data
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM response as JSON: {raw}", exc_info=True)
        # Return empty/null dict instead of crashing
        return {
            "customer_name": None,
            "cake_type": None,
            "flavour": None,
            "size_kg": None,
            "delivery_date": None,
            "delivery_address": None,
            "special_notes": None,
        }
    except APITimeoutError as e:
        logger.error(f"LLM API timeout during extraction: {e}", exc_info=True)
        raise
    except APIError as e:
        logger.error(f"LLM API error during extraction: {e}", exc_info=True)
        raise
    except Exception as e:
        logger.error(f"Unexpected error during extraction: {e}", exc_info=True)
        raise
