"""
Test script to simulate a full WhatsApp conversation
without needing actual WhatsApp or Twilio.

Usage:
    python test_conversation.py

Make sure the server is running at http://localhost:8000 first.
"""

import httpx
import time
import sys

BASE_URL = "http://localhost:8000"
TEST_PHONE = "whatsapp:+919999999999"

# Simulated customer messages — a realistic ordering flow
MESSAGES = [
    "Hi, I want to order a cake",
    "My name is Aryan",
    "I want a chocolate cake",
    "Chocolate truffle flavour please",
    "1.5 kg",
    "This Sunday, March 30th",
    "42, MG Road, Bengaluru 560001",
    "Please write 'Happy Birthday Priya' on it",
    "Yes, that looks perfect. Please confirm the order.",
]


def test_health():
    """Check if the server is running."""
    print("=" * 60)
    print("  Sweet Moments — Conversation Simulator")
    print("=" * 60)
    print()

    try:
        r = httpx.get(f"{BASE_URL}/health", timeout=5)
        if r.status_code == 200:
            print("✅ Server is healthy:", r.json())
            return True
        else:
            print(f"❌ Health check failed: {r.status_code}")
            return False
    except httpx.ConnectError:
        print("❌ Cannot connect to server at", BASE_URL)
        print("   Make sure to run: docker compose up --build")
        return False


def send_message(message: str, step: int):
    """Send a simulated WhatsApp message to the webhook."""
    print(f"\n{'─' * 50}")
    print(f"  Step {step}/{len(MESSAGES)}")
    print(f"{'─' * 50}")
    print(f"📱 Customer: {message}")
    print()

    try:
        r = httpx.post(
            f"{BASE_URL}/webhook/whatsapp",
            data={
                "Body": message,
                "From": TEST_PHONE,
            },
            timeout=30,  # LLM calls can take a few seconds
        )

        if r.status_code == 200:
            print(f"✅ Sent successfully (status: {r.status_code})")
        else:
            print(f"⚠️  Unexpected status: {r.status_code}")
            print(f"   Response: {r.text[:200]}")

    except httpx.ReadTimeout:
        print("⏳ Request timed out (LLM may be slow)")
    except Exception as e:
        print(f"❌ Error: {e}")


def check_dashboard():
    """Check if the dashboard has orders."""
    print(f"\n{'═' * 60}")
    print("  Checking Dashboard")
    print(f"{'═' * 60}")

    try:
        r = httpx.get(f"{BASE_URL}/dashboard", timeout=10)
        if r.status_code == 200:
            if "No orders yet" in r.text:
                print("📋 Dashboard loaded — no orders saved yet")
                print("   (The bot may not have reached [ORDER_COMPLETE])")
            else:
                # Count order cards by looking for the card class
                order_count = r.text.count('class="card"')
                print(f"📋 Dashboard loaded — {order_count} order(s) found!")
            print(f"\n   🌐 View at: {BASE_URL}/dashboard")
        else:
            print(f"⚠️  Dashboard returned status: {r.status_code}")
    except Exception as e:
        print(f"❌ Error loading dashboard: {e}")


def main():
    if not test_health():
        sys.exit(1)

    print("\n🚀 Starting simulated conversation...\n")
    print(f"   Phone: {TEST_PHONE}")
    print(f"   Messages: {len(MESSAGES)}")

    for i, msg in enumerate(MESSAGES, 1):
        send_message(msg, i)
        # Small delay between messages to simulate real typing
        if i < len(MESSAGES):
            time.sleep(2)

    print()
    time.sleep(2)
    check_dashboard()

    print(f"\n{'═' * 60}")
    print("  ✨ Simulation complete!")
    print(f"{'═' * 60}")
    print()
    print("  Next steps:")
    print(f"  1. Open {BASE_URL}/dashboard in your browser")
    print("  2. Check if the order appeared")
    print("  3. Connect Twilio sandbox for real WhatsApp testing")
    print()


if __name__ == "__main__":
    main()
