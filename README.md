# 🍰 Sweet Moments — AI WhatsApp Ordering Bot

An end-to-end AI-powered WhatsApp bot that takes customer cake orders via natural conversation, extracts structured order data, and displays it on a live auto-refreshing dashboard for the shopkeeper.

Build with **Python**, **FastAPI**, **Twilio**, **OpenRouter (GPT-4o-mini)**, **PostgreSQL**, and **HTMX**.

---

## ✨ Features

- **Conversational AI**: Uses `gpt-4o-mini` to chat naturally with customers and collect order details step-by-step (Name, Cake Type, Size, Delivery Date, Address, Special Notes).
- **Automated Data Extraction**: A second, hidden LLM call cleanly extracts the finished conversation into structured JSON data.
- **Persistent Memory**: Uses PostgreSQL to save chat histories per phone number, allowing for multi-turn conversations.
- **Real-Time Dashboard**: A premium, dark-mode web dashboard built with HTML/CSS and **HTMX**. It automatically refreshes every 20 seconds to show new orders without reloading the page.
- **Dockerized**: Fully containerized backend and database for easy local setup.

---

## 🏗️ Architecture

1. **Twilio Webhook**: Receives WhatsApp messages and forwards them to the FastAPI server.
2. **FastAPI Engine**: Manages the conversation state and triggers the OpenAI API calls.
3. **OpenRouter/OpenAI API**: Acts as the "brain," generating conversational replies and parsing structural data.
4. **PostgreSQL Database**: Stores active conversations and finalized extracted `Orders`.
5. **HTMX Frontend**: Serves the `/dashboard` endpoint directly from FastAPI, updating the UI dynamically.

---

## 🚀 How to Run Locally

### 1. Prerequisites
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running.
- [Ngrok](https://ngrok.com/) for exposing your local server to Twilio.
- An OpenRouter or OpenAI API Key.
- A Twilio account (free tier works fine for the Sandbox).

### 2. Environment Setup
Create a `.env` file in the root directory and add your keys:
```env
DATABASE_URL=postgresql+asyncpg://postgres:password@db:5432/cakebot
OPENAI_API_KEY=sk-or-v1-your-openrouter-key
TWILIO_ACCOUNT_SID=ACyour-twilio-sid
TWILIO_AUTH_TOKEN=your-twilio-auth-token
TWILIO_WHATSAPP_NUMBER=whatsapp:+14155238886
```
*(Note: If you are using standard OpenAI instead of OpenRouter, you'll need to remove `base_url="https://openrouter.ai/api/v1"` in `app/bot.py`)*

### 3. Start the Server
Run the application using Docker Compose:
```bash
docker compose up --build -d
```
The FastAPI web server will start on port `8000`, and the PostgreSQL database on port `5432`.

Verify the server is healthy:
```bash
curl http://localhost:8000/health
# Expected: {"status": "ok"}
```

View the live dashboard:
**[http://localhost:8000/dashboard](http://localhost:8000/dashboard)**

---

## 🧪 Testing the Bot (No WhatsApp Needed)

You can simulate a full WhatsApp conversation directly against the local server using the included test script. This is great for debugging the AI without setting up Twilio.

```bash
# Run the simulation
docker compose exec web python test_conversation.py
```
This will send 9 sequential messages simulating a realistic customer order. Watch your dashboard — the order will magically appear when the script finishes!

---

## 📱 Connecting to Real WhatsApp

To connect the bot to actual WhatsApp accounts, use the Twilio Sandbox:

1. **Start Ngrok**:
   ```bash
   ngrok http 8000
   ```
   *Copy the Forwarding URL (e.g., `https://1234-abcd.ngrok-free.app`)*
2. **Configure Twilio**:
   - Go to your Twilio Console → **Messaging** → **Try it out** → **Send a WhatsApp message**.
   - Under Sandbox Settings, paste your Ngrok URL followed by the webhook path:
     `https://1234-abcd.ngrok-free.app/webhook/whatsapp`
   - Set the method to `HTTP POST`.
3. **Send a Message**: Follow the Twilio instructions to join the sandbox from your phone, then send a message like *"Hi, I'd like to order a cake!"*

---

## 📂 Project Structure

```text
├── app/
│   ├── templates/
│   │   └── dashboard.html    # Premium HTMX dashboard UI
│   ├── __init__.py
│   ├── bot.py                # AI system prompts and OpenRouter logic
│   ├── config.py             # Environment variables loader
│   ├── database.py           # Async SQLAlchemy Postgres setup
│   ├── main.py               # FastAPI web server and Twilio Webhook
│   └── models.py             # Database tables (Conversations & Orders)
├── .env                      # API Keys (git-ignored)
├── docker-compose.yml        # Docker orchestration
├── Dockerfile                # Python environment build
├── requirements.txt          # Dependencies
└── test_conversation.py      # Automated E2E testing simulator
```
