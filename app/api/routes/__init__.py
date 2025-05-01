from fastapi import APIRouter

from .health import router as health_router
from .media import router as media_router
from .tasks import router as tasks_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(tasks_router)
api_router.include_router(media_router)
