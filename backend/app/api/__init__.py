from fastapi import APIRouter

from .datasets import router as datasets_router
from .detection import router as detection_router
from .governance import router as governance_router
from .replay import router as replay_router
from .windows import router as windows_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(datasets_router)
api_router.include_router(replay_router)
api_router.include_router(windows_router)
api_router.include_router(governance_router)
api_router.include_router(detection_router)

__all__ = ["api_router"]
