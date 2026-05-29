"""FastAPI application factory for Voiceorder-AI."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.v1.dashboard import router as dashboard_router
from app.api.v1.health import router as health_router
from app.api.v1.orders import router as orders_router
from app.api.v1.webhook import router as webhook_router
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import get_logger
from app.core.security import rate_limiter
from app.db.base import Base
from app.db.session import engine
from app.middleware import register_middleware

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown."""
    logger.info("Starting up application")

    # Import model package so SQLAlchemy metadata is populated before create_all.
    import app.models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created/verified")

    yield

    logger.info("Shutting down application")
    rate_limiter.cleanup_old_entries()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="AI BOT SERVICE",
        description="AI-powered WhatsApp bot for cake ordering",
        version="2.0.0",
        lifespan=lifespan,
    )

    register_middleware(app, settings)
    register_exception_handlers(app)

    app.mount("/static", StaticFiles(directory="static"), name="static")
    app.include_router(health_router)
    app.include_router(webhook_router)
    app.include_router(dashboard_router)
    app.include_router(orders_router)

    return app


app = create_app()
