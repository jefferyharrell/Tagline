from fastapi import APIRouter

from .admin import router as admin_router
from .auth import router as auth_router
from .diagnostics import router as diagnostics_router
from .events import router as events_router
from .health import router as health_router
from .library import router as library_router
from .logs import router as logs_router
from .media import router as media_router
from .search import router as search_router
from .storage import router as storage_router

public_router = APIRouter()
private_router = APIRouter()

# All public endpoints go on public_router
public_router.include_router(health_router)
public_router.include_router(auth_router, prefix="/auth", tags=["authentication"])

# All protected endpoints go on private_router
private_router.include_router(admin_router, prefix="/admin", tags=["admin"])
private_router.include_router(diagnostics_router, prefix="/diagnostics", tags=["diagnostics"])
private_router.include_router(events_router, prefix="/events", tags=["events"])
private_router.include_router(library_router, prefix="/library", tags=["library"])
private_router.include_router(logs_router, prefix="/logs", tags=["logs"])
private_router.include_router(media_router)
private_router.include_router(search_router, prefix="/search", tags=["search"])
private_router.include_router(storage_router, prefix="/storage", tags=["storage"])
