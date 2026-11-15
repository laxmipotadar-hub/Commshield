from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import api_router
from .api.replay import router as replay_router
from .api.windows import list_windows
from .database import Base, engine
from .schemas import PaginatedWindowsResponse
from . import models  # noqa: F401


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create all database tables on startup
    Base.metadata.create_all(bind=engine)
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

# Also expose unversioned /api/replay and /api/traffic/windows per specification
app.include_router(replay_router, prefix="/api")
app.get("/api/traffic/windows", response_model=PaginatedWindowsResponse, tags=["Windows & Detection"])(list_windows)


@app.get("/api/health")
def health_check():
    return {"status": "ok"}
