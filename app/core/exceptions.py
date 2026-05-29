"""Application exception handlers."""

import json

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from app.core.logging import get_logger
from app.schemas.order import ErrorResponse

logger = get_logger(__name__)


async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions with structured JSON output."""
    logger.warning("HTTP %s: %s", exc.status_code, exc.detail)
    detail = exc.detail if isinstance(exc.detail, str) else json.dumps(exc.detail, ensure_ascii=False)
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error=f"HTTP {exc.status_code}",
            detail=detail,
            status_code=exc.status_code,
        ).model_dump(),
        headers=exc.headers,
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register application-wide exception handlers."""
    app.add_exception_handler(HTTPException, http_exception_handler)
