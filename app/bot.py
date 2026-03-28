from openai import AsyncOpenAI
from app.config import settings
import json

client = AsyncOpenAI(
    api_key=settings.OPENAI_API_KEY,
    base_url="https://openrouter.ai/api/v1"
)

# ── System prompt ──────────────────────────────────────────────
SYSTEM_PROMPT = """
You are a friendly WhatsApp assistant for "Sweet Moments" cake shop.
Your job is to take cake orders from customers over WhatsApp chat.

CONVERSATION FLOW:
1. Greet the customer warmly (first message only)
2. Ask what kind of cake they want
3. Collect all these details one by one (don't ask all at once):
   - Customer name
   - Cake type (e.g. chocolate, vanilla, black forest, red velvet, photo cake)
   - Flavour / theme if applicable
   - Size in kg (e.g. 0.5kg, 1kg, 2kg)
   - Delivery date
   - Delivery address
   - Any special notes (message on cake, dietary needs, etc.)
4. Once you have everything, confirm the full order back to the customer
5. After they confirm, say thank you and end with exactly this tag on its own line:
   [ORDER_COMPLETE]

RULES:
- Keep messages short, friendly, and conversational
- Ask one question at a time
- If the customer gives multiple details at once, acknowledge all of them
- Do not make up prices — say "the shopkeeper will confirm pricing shortly"
- Only output [ORDER_COMPLETE] after the customer has confirmed the order
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


# ── Chat function ──────────────────────────────────────────────
async def chat(history: list[dict], user_message: str) -> tuple[str, bool]:
    """
    Send user message, get bot reply.
    Returns (reply_text, order_is_complete)
    """
    history.append({"role": "user", "content": user_message})

    response = await client.chat.completions.create(
        model="openai/gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            *history
        ],
        max_tokens=300,
        temperature=0.7,
    )

    reply = response.choices[0].message.content.strip()
    history.append({"role": "assistant", "content": reply})

    order_complete = "[ORDER_COMPLETE]" in reply
    # Clean the tag from what customer sees
    clean_reply = reply.replace("[ORDER_COMPLETE]", "").strip()

    return clean_reply, order_complete


# ── Extract order details from full conversation ───────────────
async def extract_order(history: list[dict]) -> dict:
    """
    After conversation ends, run a second LLM call
    purely to extract structured data. Returns a dict.
    """
    conversation_text = "\n".join(
        f"{msg['role'].upper()}: {msg['content']}"
        for msg in history
    )

    response = await client.chat.completions.create(
        model="openai/gpt-4o-mini",
        messages=[
            {
                "role": "user",
                "content": EXTRACT_PROMPT + conversation_text
            }
        ],
        max_tokens=300,
        temperature=0,  # deterministic for extraction
    )

    raw = response.choices[0].message.content.strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # Fallback: return empty dict, order still saved with transcript
        return {}
