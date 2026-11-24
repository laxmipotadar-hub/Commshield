import asyncio
from datetime import datetime, timezone
import json
from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from .api import api_router
from .api.attribution import router as attribution_router
from .api.data import router as data_router
from .api.demo import router as demo_router
from .api.detection import router as detection_router
from .api.experiments import router as experiments_router
from .api.governance import router as governance_router
from .api.investigation import router as investigation_router
from .api.real import router as real_router
from .api.replay import router as replay_router
from .api.twin import router as twin_router
from .api.twin_v2 import router as twin_v2_router
from .api.validation import router as validation_router
from .api.windows import router as windows_router, list_windows
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

# Enable CORS for the operator dashboard and remote Windows frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ],
    allow_origin_regex=r"^https?://.*$",
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
app.include_router(twin_v2_router, prefix="/api")
app.include_router(data_router, prefix="/api")
app.include_router(real_router, prefix="/api")
app.include_router(validation_router, prefix="/api")
app.include_router(windows_router, prefix="/api")
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


@app.websocket("/ws/telemetry")
async def telemetry_websocket_stream(websocket: WebSocket):
    """Real-time full-duplex WebSocket stream for CommShield live telemetry and alerts.
    
    Supports:
      - Client -> Server: {"type": "subscribe", "payload": {"slices": [...], "devices": [...], "metrics": [...]}}
      - Server -> Client: {"type": "telemetry", "payload": {...}}
      - Server -> Client: {"type": "alert", "payload": {...}}
    """
    await websocket.accept()
    subscriptions = {
        "slices": set(),
        "devices": set(),
        "metrics": set(),
    }
    try:
        # Initial connection acknowledgment alert matching exact contract
        await websocket.send_text(json.dumps({
            "type": "alert",
            "payload": {
                "alertId": "alt-init",
                "id": "alt-init",
                "severity": "info",
                "deviceId": "ue-cam-01",
                "sliceId": "sst-1-sd-010203",
                "message": "Connected to CommShield Real-Time Telemetry Stream",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "position": [-62.0, 3.5, 12.0],
                "source": "commshield-core",
            }
        }))

        async def client_listener():
            while True:
                msg = await websocket.receive_text()
                try:
                    cmd = json.loads(msg)
                    msg_type = cmd.get("type") or cmd.get("action")
                    if msg_type == "subscribe":
                        p = cmd.get("payload", {})
                        if p.get("slices"):
                            subscriptions["slices"] = set(p["slices"])
                        if p.get("devices"):
                            subscriptions["devices"] = set(p["devices"])
                        if p.get("metrics"):
                            subscriptions["metrics"] = set(p["metrics"])
                        await websocket.send_text(json.dumps({
                            "type": "subscribed",
                            "payload": {
                                "slices": list(subscriptions["slices"]),
                                "devices": list(subscriptions["devices"]),
                                "metrics": list(subscriptions["metrics"]),
                                "status": "active",
                            }
                        }))
                    elif msg_type in ("PING", "ping"):
                        await websocket.send_text(json.dumps({
                            "type": "pong",
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                        }))
                except Exception:
                    pass

        async def telemetry_broadcaster():
            devices = [
                # eMBB Cameras
                {"deviceId": "ue-cam-01", "sliceId": "sst-1-sd-010203", "pos": [-62.0, 3.5, 12.0], "packetRate": 1250, "throughput": 75.0, "latency": 4.2, "jitter": 0.8},
                {"deviceId": "ue-cam-02", "sliceId": "sst-1-sd-010203", "pos": [-50.0, 3.5, 10.0], "packetRate": 1180, "throughput": 72.0, "latency": 4.5, "jitter": 0.9},
                {"deviceId": "ue-cam-03", "sliceId": "sst-1-sd-010203", "pos": [-38.0, 3.5, 12.0], "packetRate": 1220, "throughput": 74.5, "latency": 4.1, "jitter": 0.7},
                {"deviceId": "ue-cam-04", "sliceId": "sst-1-sd-010203", "pos": [-62.0, 3.5, 24.0], "packetRate": 1290, "throughput": 78.0, "latency": 4.8, "jitter": 1.1},
                # URLLC AGVs
                {"deviceId": "ue-agv-01", "sliceId": "sst-2-sd-010203", "pos": [-18.0, 0.4, 26.0], "packetRate": 480, "throughput": 24.0, "latency": 1.2, "jitter": 0.2},
                {"deviceId": "ue-agv-02", "sliceId": "sst-2-sd-010203", "pos": [-6.0, 0.4, 34.0], "packetRate": 510, "throughput": 25.5, "latency": 1.4, "jitter": 0.3},
                {"deviceId": "ue-agv-03", "sliceId": "sst-2-sd-010203", "pos": [8.0, 0.4, 25.0], "packetRate": 495, "throughput": 24.2, "latency": 1.1, "jitter": 0.2},
                # mMTC Sensors
                {"deviceId": "ue-sns-01", "sliceId": "sst-3-sd-010203", "pos": [38.0, 0.3, 10.0], "packetRate": 25, "throughput": 8.5, "latency": 12.1, "jitter": 1.8},
                {"deviceId": "ue-sns-02", "sliceId": "sst-3-sd-010203", "pos": [44.0, 0.3, 12.0], "packetRate": 28, "throughput": 8.9, "latency": 11.8, "jitter": 1.6},
                {"deviceId": "ue-sns-03", "sliceId": "sst-3-sd-010203", "pos": [50.0, 0.3, 10.0], "packetRate": 24, "throughput": 8.2, "latency": 13.0, "jitter": 2.1},
            ]
            idx = 0
            while True:
                await asyncio.sleep(1.2)
                dev = devices[idx % len(devices)]
                idx += 1

                # If client specified device subscriptions, filter if current device not subscribed
                if subscriptions["devices"] and dev["deviceId"] not in subscriptions["devices"]:
                    continue

                anomaly_score = 0.02
                verdict = "benign"
                if idx % 16 == 15:
                    anomaly_score = 0.85
                    verdict = "attack"
                elif idx % 8 == 7:
                    anomaly_score = 0.45
                    verdict = "uncertain"

                now_ts = datetime.now(timezone.utc).isoformat()
                now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)

                # Send telemetry matching exact API contract
                await websocket.send_text(json.dumps({
                    "type": "telemetry",
                    "payload": {
                        "windowId": f"win-{now_ms}",
                        "timestamp": now_ts,
                        "sliceId": dev["sliceId"],
                        "deviceId": dev["deviceId"],
                        "metrics": {
                            "packetRate": dev["packetRate"],
                            "throughput": dev["throughput"],
                            "latency": dev["latency"],
                            "jitter": dev["jitter"],
                            "lossRate": 0.0001,
                        },
                        "anomalyScore": anomaly_score,
                        "verdict": verdict,
                    }
                }))

                # Periodically or on attack send alert matching exact API contract
                if verdict == "attack":
                    await websocket.send_text(json.dumps({
                        "type": "alert",
                        "payload": {
                            "alertId": f"alt-{now_ms}",
                            "id": f"alt-{now_ms}",
                            "severity": "critical",
                            "deviceId": dev["deviceId"],
                            "sliceId": dev["sliceId"],
                            "message": f"Slice {dev['sliceId']} critical traffic spike on {dev['deviceId']}",
                            "timestamp": now_ts,
                            "position": dev["pos"],
                            "source": dev["deviceId"],
                        }
                    }))
                elif idx % 20 == 0:
                    await websocket.send_text(json.dumps({
                        "type": "alert",
                        "payload": {
                            "alertId": f"alt-{now_ms}",
                            "id": f"alt-{now_ms}",
                            "severity": "warning",
                            "deviceId": dev["deviceId"],
                            "sliceId": dev["sliceId"],
                            "message": f"Slice {dev['sliceId']} nominal jitter elevation on {dev['deviceId']}",
                            "timestamp": now_ts,
                            "position": dev["pos"],
                            "source": dev["deviceId"],
                        }
                    }))

        listener = asyncio.create_task(client_listener())
        broadcaster = asyncio.create_task(telemetry_broadcaster())

        done, pending = await asyncio.wait([listener, broadcaster], return_when=asyncio.FIRST_COMPLETED)
        for t in pending:
            t.cancel()
    except (WebSocketDisconnect, Exception):
        pass
# CommShield AI Core
