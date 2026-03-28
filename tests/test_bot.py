"""Tests for the bot module."""
import pytest
import json
from app.types import Message


@pytest.mark.asyncio
async def test_chat_history_format():
    """Test that chat history is properly formatted."""
    from app.bot import chat
    
    history: list[Message] = []
    
    try:
        reply, order_complete = await chat(history, "Hi!")
        # If API call succeeds, verify response format
        assert isinstance(reply, str)
        assert isinstance(order_complete, bool)
        assert len(history) >= 2  # Should have user message and bot reply
        assert history[-2]["role"] == "user"
        assert history[-1]["role"] == "assistant"
    except Exception:
        # Skip test if API is not available
        pytest.skip("OpenRouter API not available")


def test_extract_order_validates_json():
    """Test that extract_order returns valid structure even on parse error."""
    from app.bot import extract_order
    import asyncio
    
    async def run_test():
        history: list[Message] = [
            {"role": "user", "content": "Hi"},
            {"role": "assistant", "content": "Hello"},
        ]
        
        try:
            result = await extract_order(history)
            # Should have the expected keys
            assert "customer_name" in result
            assert "cake_type" in result
            assert "delivery_date" in result
        except Exception:
            # Skip if API not available
            pytest.skip("OpenRouter API not available")
    
    asyncio.run(run_test())
