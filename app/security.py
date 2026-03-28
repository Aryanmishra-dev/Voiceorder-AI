"""Security utilities including rate limiting and webhook validation."""
from datetime import datetime, timedelta
from typing import Dict
from fastapi import HTTPException, Request
from twilio.request_validator import RequestValidator
from app.config import settings
from app.logger import get_logger

logger = get_logger(__name__)


class RateLimiter:
    """Simple in-memory rate limiter for webhook endpoints."""
    
    def __init__(
        self,
        max_requests: int = settings.RATE_LIMIT_REQUESTS,
        window_seconds: int = settings.RATE_LIMIT_WINDOW_SECONDS
    ):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: Dict[str, list[datetime]] = {}
    
    def is_allowed(self, key: str) -> bool:
        """Check if request is allowed for the given key."""
        now = datetime.utcnow()
        cutoff = now - timedelta(seconds=self.window_seconds)
        
        if key not in self.requests:
            self.requests[key] = []
        
        # Remove old requests outside the window
        self.requests[key] = [
            req_time for req_time in self.requests[key]
            if req_time > cutoff
        ]
        
        # Check if limit exceeded
        if len(self.requests[key]) >= self.max_requests:
            logger.warning(f"Rate limit exceeded for {key}")
            return False
        
        # Record this request
        self.requests[key].append(now)
        return True
    
    def cleanup_old_entries(self) -> None:
        """Remove entries with no recent requests (memory optimization)."""
        now = datetime.utcnow()
        cutoff = now - timedelta(seconds=self.window_seconds * 2)
        
        keys_to_delete = []
        for key, requests in self.requests.items():
            if all(req_time <= cutoff for req_time in requests):
                keys_to_delete.append(key)
        
        for key in keys_to_delete:
            del self.requests[key]


# Global rate limiter instance
rate_limiter = RateLimiter()


class TwilioWebhookValidator:
    """Validates Twilio webhook signatures."""
    
    def __init__(self, auth_token: str):
        self.validator = RequestValidator(auth_token)
    
    def validate(self, url: str, params: dict, signature: str) -> bool:
        """Validate webhook signature."""
        is_valid = self.validator.validate(url, params, signature)
        if not is_valid:
            logger.warning(f"Invalid Twilio webhook signature from {params.get('From', 'unknown')}")
        return is_valid


# Global webhook validator instance
webhook_validator = TwilioWebhookValidator(settings.TWILIO_AUTH_TOKEN)


async def validate_twilio_webhook(
    request: Request,
    url: str,
    params: dict
) -> bool:
    """Validate incoming Twilio webhook."""
    if not settings.ENABLE_WEBHOOK_VALIDATION:
        return True
    
    signature = request.headers.get("X-Twilio-Signature", "")
    if not signature:
        logger.error("Missing X-Twilio-Signature header")
        return False
    
    return webhook_validator.validate(url, params, signature)


def check_rate_limit(identifier: str) -> None:
    """Check rate limit for an identifier (e.g., phone number)."""
    if not settings.RATE_LIMIT_ENABLED:
        return
    
    if not rate_limiter.is_allowed(identifier):
        raise HTTPException(
            status_code=429,
            detail="Too many requests. Please try again later."
        )
