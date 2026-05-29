# Twilio Setup

1. Configure your Twilio WhatsApp sender.
2. Set the incoming message webhook to `https://your-domain.example/webhook/whatsapp`.
3. Use `POST` as the webhook method.
4. Set `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, and `TWILIO_WHATSAPP_NUMBER` in the app environment.
5. Keep `ENABLE_WEBHOOK_VALIDATION=true` outside local test scenarios.
