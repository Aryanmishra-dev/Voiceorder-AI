"""Trusted host middleware configuration."""

from fastapi import FastAPI
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.core.config import Settings


def add_trusted_host_middleware(app: FastAPI, settings: Settings) -> None:
    """Register trusted host validation middleware."""
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.trusted_hosts)
