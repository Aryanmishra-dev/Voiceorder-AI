"""Tests for security and rate limiting functionality."""
import pytest
from app.security import RateLimiter, rate_limiter
from datetime import datetime


def test_rate_limiter_allows_under_limit():
    """Test that rate limiter allows requests under the limit."""
    limiter = RateLimiter(max_requests=5, window_seconds=60)
    
    for i in range(5):
        assert limiter.is_allowed("test_user") is True


def test_rate_limiter_blocks_over_limit():
    """Test that rate limiter blocks requests over the limit."""
    limiter = RateLimiter(max_requests=2, window_seconds=60)
    
    assert limiter.is_allowed("test_user") is True
    assert limiter.is_allowed("test_user") is True
    assert limiter.is_allowed("test_user") is False


def test_rate_limiter_different_keys():
    """Test that rate limiter treats different users separately."""
    limiter = RateLimiter(max_requests=1, window_seconds=60)
    
    assert limiter.is_allowed("user1") is True
    assert limiter.is_allowed("user1") is False
    assert limiter.is_allowed("user2") is True
    assert limiter.is_allowed("user2") is False


def test_rate_limiter_cleanup():
    """Test that cleanup removes old entries."""
    limiter = RateLimiter(max_requests=10, window_seconds=1)
    
    # Add some requests
    limiter.is_allowed("user1")
    assert "user1" in limiter.requests
    
    # Cleanup should not remove recent entries
    limiter.cleanup_old_entries()
    assert "user1" in limiter.requests
