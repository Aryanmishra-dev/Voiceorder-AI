# API Endpoints

| Endpoint | Method | Auth | Description |
|---|---|---|---|
| `/health` | GET | Public | Health check |
| `/webhook/whatsapp` | POST | Twilio signature | WhatsApp webhook receiver |
| `/dashboard` | GET | Admin | Dashboard HTML |
| `/api/v1/orders` | GET | Admin | Paginated order list |
| `/api/v1/order/{order_id}/status` | POST | Admin | JSON order status update |
| `/order/{order_id}/status` | POST | Admin | HTMX order status update |

Admin routes accept either `X-API-Key` or HTTP Basic credentials.
