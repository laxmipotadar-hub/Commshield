from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from .api import api_router
from .api.attribution import router as attribution_router
from .api.demo import router as demo_router
from .api.detection import router as detection_router
from .api.experiments import router as experiments_router
from .api.governance import router as governance_router
from .api.investigation import router as investigation_router
from .api.replay import router as replay_router
from .api.twin import router as twin_router
from .api.windows import list_windows
from .database import Base, engine, get_db
from .schemas import PaginatedWindowsResponse
from .services.system import reset_runtime_database
from . import models  # noqa: F401


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create all database tables on startup
    Base.metadata.create_all(bind=engine)
    # Ensure per-slice anchor baselines are trained and registered once
    db = None
    try:
        from .database import SessionLocal
        from .models import BaselineRegistry
        db = SessionLocal()
        reg_count = db.query(BaselineRegistry).count()
        if reg_count == 0:
            from ml_engine.baseline.trainer import train_all_baselines
            train_all_baselines(db=db)
    except Exception as e:
        import logging
        logging.getLogger("commshield").warning("Baseline initialization deferred: %s", e)
    finally:
        if db:
            db.close()
    yield


app = FastAPI(
    title="CommShield API",
    version="1.0.0",
    lifespan=lifespan,
)

# Enable CORS for the operator dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API v1 routers
app.include_router(api_router)

# Also expose unversioned endpoints per specification
app.include_router(replay_router, prefix="/api")
app.include_router(detection_router, prefix="/api")
app.include_router(governance_router, prefix="/api")
app.include_router(attribution_router, prefix="/api")
app.include_router(investigation_router, prefix="/api")
app.include_router(experiments_router, prefix="/api")
app.include_router(demo_router, prefix="/api")
app.include_router(twin_router, prefix="/api")
app.get("/api/traffic/windows", response_model=PaginatedWindowsResponse, tags=["Windows & Detection"])(list_windows)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={"detail": str(exc)},
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    import logging
    logging.getLogger("commshield").error("Unhandled exception on %s: %s", request.url.path, exc)
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal server error: {str(exc)}"},
    )


@app.get("/api/health")
def health_check():
    return {"status": "ok"}


@app.post("/api/reset", tags=["System"])
@app.post("/api/v1/reset", tags=["System"])
def reset_database_endpoint(db: Session = Depends(get_db)):
    """Reset runtime database tables while preserving calibrated anchor baselines."""
    return reset_runtime_database(db=db)
