import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api.v1.routes import private_router, public_router
from app.api.v1.routes.auth import limiter
from app.auth_utils import get_current_user
from app.config import StorageProviderType, get_settings
from app.structlog_config import configure_structlog

# Define required environment variables for each storage provider
PROVIDER_REQUIRED_VARS = {
    StorageProviderType.FILESYSTEM: ["FILESYSTEM_ROOT_PATH"],
    StorageProviderType.DROPBOX: [
        "DROPBOX_APP_KEY",
        "DROPBOX_APP_SECRET",
        "DROPBOX_REFRESH_TOKEN",
    ],
    # Add other providers here
}


def validate_config_on_startup(settings):
    """Checks provider-specific config variables after basic settings are loaded."""
    provider = settings.STORAGE_PROVIDER
    required_vars = PROVIDER_REQUIRED_VARS.get(provider, [])
    missing = []

    for var in required_vars:
        if not getattr(settings, var, None):
            missing.append(var)

    if missing:
        logging.critical(
            f"Missing required config for storage provider '{provider.value}': {', '.join(missing)}"
        )
        raise RuntimeError(
            f"Missing required config for storage provider '{provider.value}': {', '.join(missing)}"
        )


@asynccontextmanager
async def lifespan(app):

    logging.info("Starting application...")

    logging.info("Loading settings...")
    try:
        settings = get_settings()
    except ValidationError as e:
        logging.critical(f"Configuration error:\n{e}")
        raise RuntimeError(f"Configuration error: {e}")
    logging.info("Loading settings complete.")

    # Configure structlog for the main application
    configure_structlog(
        service_name="tagline-backend",
        log_level=settings.LOG_LEVEL,
        log_format=settings.LOG_FORMAT,
    )
    logging.info(f"Log level set to {logging.getLevelName(settings.LOG_LEVEL)}")

    logging.info("Validating configuration...")
    validate_config_on_startup(settings)
    logging.info("Configuration validation complete.")

    logging.info("Application startup complete.")
    yield


app = FastAPI(
    title="Tagline Media Management API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# Configure rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")


# Direct route to pretty UI
@app.get("/elements", include_in_schema=False)
async def custom_docs():
    return FileResponse("app/static/elements.html")


# Public endpoints (e.g., /v1/health)
app.include_router(public_router, prefix="/v1")

# Protected endpoints (all others)
app.include_router(
    private_router, prefix="/v1", dependencies=[Depends(get_current_user)]
)
