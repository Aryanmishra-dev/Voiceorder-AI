"""Security utilities including rate limiting and webhook validation."""
from collections import deque
from datetime import datetime, timedelta, timezone
from threading import Lock
from typing import Deque
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
        window_seconds: int = settings.RATE_LIMIT_WINDOW_SECONDS,
        max_identifiers: int = settings.RATE_LIMIT_MAX_IDENTIFIERS,
    ):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.max_identifiers = max_identifiers
        self.requests: dict[str, Deque[datetime]] = {}
        self._lock = Lock()

    def is_allowed(self, key: str) -> bool:
        """Check if request is allowed for the given key."""
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(seconds=self.window_seconds)

        with self._lock:
            if key not in self.requests:
                if len(self.requests) >= self.max_identifiers:
                    self._cleanup_old_entries(cutoff)
                    if len(self.requests) >= self.max_identifiers:
                        logger.warning("Rate limiter identifier capacity reached")
                        return False
                self.requests[key] = deque()

            history = self.requests[key]

            # Drop entries outside the active rate-limit window.
            while history and history[0] <= cutoff:
                history.popleft()

            if len(history) >= self.max_requests:
                logger.warning("Rate limit exceeded for %s", mask_identifier(key))
                return False

            history.append(now)
            return True

    def cleanup_old_entries(self) -> None:
        """Remove entries with no recent requests (memory optimization)."""
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(seconds=self.window_seconds * 2)

        with self._lock:
            self._cleanup_old_entries(cutoff)

    def _cleanup_old_entries(self, cutoff: datetime) -> None:
        """Internal cleanup. Caller must hold lock."""
        keys_to_delete = []
        for key, history in self.requests.items():
            while history and history[0] <= cutoff:
                history.popleft()
            if not history:
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
            logger.warning(
                "Invalid Twilio webhook signature from %s",
                mask_identifier(params.get("From", "unknown")),
            )
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


def mask_identifier(identifier: str) -> str:
    """Mask an identifier before logging to reduce PII exposure."""
    clean = (identifier or "").strip()
    if len(clean) <= 4:
        return "****"
    return f"****{clean[-4:]}"
