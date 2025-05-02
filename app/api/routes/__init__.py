from fastapi import APIRouter

from .health import router as health_router
from .media import router as media_router
from .tasks import router as tasks_router

public_router = APIRouter()
private_router = APIRouter()

# All public endpoints go on public_router
public_router.include_router(health_router)

# All protected endpoints go on private_router
private_router.include_router(media_router)
private_router.include_router(tasks_router)
