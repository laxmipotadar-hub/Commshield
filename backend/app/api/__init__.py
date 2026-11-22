from fastapi import APIRouter

from .attribution import router as attribution_router
from .data import router as data_router
from .datasets import router as datasets_router
from .demo import router as demo_router
from .detection import router as detection_router
from .experiments import router as experiments_router
from .governance import router as governance_router
from .investigation import router as investigation_router
from .real import router as real_router
from .replay import router as replay_router
from .twin import router as twin_router
from .validation import router as validation_router
from .windows import router as windows_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(datasets_router)
api_router.include_router(data_router)
api_router.include_router(real_router)
api_router.include_router(replay_router)
api_router.include_router(windows_router)
api_router.include_router(governance_router)
api_router.include_router(detection_router)
api_router.include_router(attribution_router)
api_router.include_router(investigation_router)
api_router.include_router(experiments_router)
api_router.include_router(demo_router)
api_router.include_router(twin_router)
api_router.include_router(validation_router)

__all__ = ["api_router"]
# CommShield AI Core
