"""Middleware registration."""

from fastapi import FastAPI

from app.core.config import Settings
from app.middleware.cors import add_cors_middleware
from app.middleware.security_headers import add_security_headers_middleware
from app.middleware.trusted_hosts import add_trusted_host_middleware


def register_middleware(app: FastAPI, settings: Settings) -> None:
    """Register all application middleware."""
    add_trusted_host_middleware(app, settings)
    add_cors_middleware(app, settings)
    add_security_headers_middleware(app, settings)
