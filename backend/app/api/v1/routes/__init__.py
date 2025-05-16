from fastapi import APIRouter

from .auth import router as auth_router
from .health import router as health_router
from .media import router as media_router
from .tasks import router as tasks_router

public_router = APIRouter()
private_router = APIRouter()

# All public endpoints go on public_router
public_router.include_router(health_router)
public_router.include_router(auth_router, prefix="/auth", tags=["authentication"])

# All protected endpoints go on private_router
private_router.include_router(media_router)
private_router.include_router(tasks_router)
