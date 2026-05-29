"""Shared API dependencies."""

import secrets

from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader, HTTPBasic, HTTPBasicCredentials

from app.core.config import settings
from app.db.session import get_db

admin_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
admin_basic_auth = HTTPBasic(auto_error=False)


def _safe_compare(left: str, right: str) -> bool:
    """Constant-time compare wrapper."""
    return secrets.compare_digest(left.encode("utf-8"), right.encode("utf-8"))


async def require_admin(
    api_key: str | None = Security(admin_api_key_header),
    credentials: HTTPBasicCredentials | None = Security(admin_basic_auth),
) -> None:
    """Protect admin routes using API key or HTTP basic auth."""
    if api_key and _safe_compare(api_key, settings.ADMIN_API_KEY):
        return

    if credentials:
        if _safe_compare(credentials.username, settings.ADMIN_USERNAME) and _safe_compare(
            credentials.password, settings.ADMIN_PASSWORD
        ):
            return

    raise HTTPException(
        status_code=401,
        detail="Authentication required",
        headers={"WWW-Authenticate": 'Basic realm="AI BOT SERVICE Dashboard"'},
    )
