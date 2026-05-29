# AI BOT SERVICE

AI-powered WhatsApp ordering service for cake businesses. It handles customer chat, extracts order details, stores orders, and provides a protected admin dashboard.

## Highlights

- FastAPI backend with async SQLAlchemy
- WhatsApp webhook integration via Twilio
- LLM-powered conversation and order extraction
- Protected admin dashboard and order APIs
- Security controls: auth, webhook validation, rate limiting, trusted hosts, CORS, and security headers
- Test suite with coverage and dependency auditing

## Quick Start (Docker)

1. Create your environment file:

```bash
cp config/.env.example config/.env.development
```

2. Update required values in `config/.env.development`:

```env
OPENAI_API_KEY=your-openai-or-openrouter-key
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_WHATSAPP_NUMBER=whatsapp:+14155238886
ADMIN_API_KEY=replace-with-long-random-api-key
ADMIN_USERNAME=admin
ADMIN_PASSWORD=replace-with-strong-password
```

3. Start services:

```bash
docker compose -f deployment/docker/docker-compose.yml up --build -d
```

4. Verify:

```bash
curl http://localhost:8000/health
```

5. Open dashboard:

```text
http://localhost:8000/dashboard
```

## Authentication

Protected routes require either:

- `X-API-Key: <ADMIN_API_KEY>`
- HTTP Basic auth using `ADMIN_USERNAME` and `ADMIN_PASSWORD`

Protected routes:

- `/dashboard`
- `/api/v1/orders`
- `/api/v1/order/{order_id}/status`
- `/order/{order_id}/status`

## API Surface

| Endpoint | Method | Description |
|---|---|---|
| `/health` | GET | Health check |
| `/webhook/whatsapp` | POST | Twilio webhook receiver |
| `/dashboard` | GET | Admin dashboard |
| `/api/v1/orders` | GET | Paginated order list |
| `/api/v1/order/{order_id}/status` | POST | Update order status (JSON API) |
| `/order/{order_id}/status` | POST | Update order status (HTMX form) |

## Development Checks

```bash
pytest -q
python -m pip_audit -r requirements.txt
```

## Project Layout

- `app/api/`: HTTP route handlers and request dependencies
- `app/core/`: configuration, logging, auth helpers, exception handlers
- `app/db/`: SQLAlchemy base, engine, and sessions
- `app/models/`: ORM models
- `app/schemas/`: Pydantic schemas
- `app/services/`: WhatsApp, LLM, and order business logic
- `app/middleware/`: middleware registration and configuration
- `static/`: static assets served at `/static`
- `deployment/`: Docker and CI assets
- `docs/`: architecture, API, and setup guides

## License

MIT
