"""Health check routes."""

from datetime import datetime, timezone

from fastapi import APIRouter

from app.schemas.order import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Health check endpoint."""
    return HealthResponse(status="ok", timestamp=datetime.now(timezone.utc))
