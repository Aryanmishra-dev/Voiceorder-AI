# WhatsApp Order Flow

1. Twilio sends the incoming WhatsApp form payload to `POST /webhook/whatsapp`.
2. `app/api/v1/webhook.py` validates required Twilio fields, signature validation, and rate limiting.
3. `app/services/bot_service.py` loads or creates the active conversation for the customer.
4. `app/services/llm_service.py` generates the next assistant reply and detects order completion.
5. When complete, `llm_service.extract_order` extracts structured order fields.
6. `app/services/order_service.py` persists the order and clears the conversation history.
7. `app/services/twilio_service.py` sends the reply back to the customer through Twilio.
