from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.api.v1.prices import router as prices_router
from app.core.config import Settings
from app.db.database import Database
from app.services.price_query import PriceNotFoundError


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build the API application.

    Run with ``uvicorn app.main:create_app --factory``; settings are read from the
    environment when not passed explicitly.
    """
    settings = settings or Settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        async with Database(settings.database.url) as database:
            app.state.database = database
            yield

    app = FastAPI(
        title="Deribit Client API",
        description="Index prices of currencies collected from Deribit every minute.",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.include_router(prices_router, prefix="/api/v1")
    app.add_exception_handler(PriceNotFoundError, handle_price_not_found)
    return app


async def handle_price_not_found(request: Request, error: Exception) -> JSONResponse:
    return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"detail": str(error)})
