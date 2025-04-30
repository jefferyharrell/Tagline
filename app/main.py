import logging
import sys

from fastapi import FastAPI

from app.api.routes import api_router
from app.config import get_settings

settings = get_settings()

logging.basicConfig(
    stream=sys.stdout,
    level=settings.LOG_LEVEL,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

app = FastAPI(
    title="Tagline Media Management API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

app.include_router(api_router, prefix="/v1")
