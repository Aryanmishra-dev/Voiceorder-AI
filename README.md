# Happy bakerss — AI WhatsApp Cake Ordering Bot

An AI-powered WhatsApp bot that takes cake orders through natural conversation and displays them on a live dashboard.

**Tech:** Python, FastAPI, PostgreSQL, GPT-4o-mini, Twilio, HTMX

---

## Features

- Natural language conversation with GPT-4o-mini
- Automatic order data extraction
- Live HTMX dashboard with auto-refresh
- PostgreSQL database with full chat history
- Rate limiting and webhook validation
- Docker-ready with tests

---

## Quick Start

### Requirements
- Docker Desktop
- Ngrok (for local testing)
- OpenRouter/OpenAI API Key
- Twilio account

### Setup

1. Clone and navigate to directory
2. Copy `.env.example` to `.env` and fill in credentials:
   ```
   DATABASE_URL=postgresql+asyncpg://postgres:password@db:5432/cakebot
   OPENAI_API_KEY=your-key
   TWILIO_ACCOUNT_SID=your-sid
   TWILIO_AUTH_TOKEN=your-token
   TWILIO_WHATSAPP_NUMBER=whatsapp:+14155238886
   ```

3. Start server:
   ```bash
   docker compose up --build -d
   ```

4. Check health:
   ```bash
   curl http://localhost:8000/health
   ```

5. View dashboard:
   ```bash
   open http://localhost:8000/dashboard
   ```

---

## API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/webhook/whatsapp` | POST | Receive WhatsApp messages |
| `/health` | GET | Health check |
| `/dashboard` | GET | Live order dashboard |
| `/api/v1/orders` | GET | List orders with pagination |
| `/api/v1/orders/{id}` | GET | Get order details |
| `/api/v1/orders/{id}` | PUT | Update order status |

---

## Project Structure

```
app/
├── main.py           # FastAPI app & endpoints
├── bot.py            # Chat logic
├── config.py         # Configuration
├── database.py       # Database setup
├── models.py         # ORM models
├── schemas.py        # Validation
├── security.py       # Rate limiting & validation
└── templates/
    └── dashboard.html

tests/
├── test_main.py
├── test_bot.py
├── test_security.py
├── test_schemas.py
└── conftest.py
```

---

## Testing

```bash
# Run all tests
pytest -v

# Run with coverage
pytest --cov=app --cov-report=html
```

---

## Connect to WhatsApp

1. Start ngrok tunnel:
   ```bash
   ngrok http 8000
   ```

2. Add webhook URL to Twilio:
   ```
   https://your-ngrok-url.app/webhook/whatsapp
   ```

3. Join Twilio sandbox and send a test message

4. Orders appear on dashboard at `http://localhost:8000/dashboard`

---

## Database

```bash
# Access database
docker compose exec db psql -U postgres -d cakebot

# Backup
docker compose exec db pg_dump -U postgres cakebot > backup.sql

# Restore
docker compose exec -T db psql -U postgres cakebot < backup.sql
```

---

## License

MIT License - Built by Happy bakerss

For detailed documentation, see SECURITY_AUDIT.md and DEPLOYMENT.md

