# CommShield WebSocket Telemetry & Alert Contract Verification

import json
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)


def test_telemetry_websocket_contract():
    """Verify WebSocket client/server contracts:
    1. Initial alert payload
    2. Client subscribe message
    3. Server telemetry payload
    4. Alert payload schema
    5. Ping / Pong
    """
    with client.websocket_connect("/ws/telemetry") as ws:
        # 1. Initial Alert Message
        init_raw = ws.receive_text()
        init_msg = json.loads(init_raw)
        assert init_msg["type"] == "alert", f"Expected type 'alert', got {init_msg.get('type')}"
        init_payload = init_msg["payload"]
        assert "alertId" in init_payload
        assert init_payload["severity"] in ("critical", "warning", "info", "low")
        assert "deviceId" in init_payload
        assert "sliceId" in init_payload
        assert "message" in init_payload
        assert "timestamp" in init_payload
        assert "position" in init_payload
        assert len(init_payload["position"]) == 3

        # 2. Client -> Server: Subscribe message
        subscribe_msg = {
            "type": "subscribe",
            "payload": {
                "slices": ["sst-1-sd-010203", "sst-2-sd-010203", "sst-3-sd-010203"],
                "devices": ["ue-cam-01", "ue-cam-02", "ue-agv-01", "ue-sns-01"],
                "metrics": ["packetRate", "throughput", "latency", "jitter", "lossRate"],
            },
        }
        ws.send_text(json.dumps(subscribe_msg))

        # 3. Receive subscription confirmation or telemetry
        msg_raw = ws.receive_text()
        msg = json.loads(msg_raw)
        if msg["type"] == "subscribed":
            assert "slices" in msg["payload"]
            assert "devices" in msg["payload"]
            assert "metrics" in msg["payload"]
            # Next message should be telemetry or alert
            msg_raw = ws.receive_text()
            msg = json.loads(msg_raw)

        # 4. Validate telemetry payload schema
        assert msg["type"] in ("telemetry", "alert")
        if msg["type"] == "telemetry":
            tp = msg["payload"]
            assert "windowId" in tp
            assert "timestamp" in tp
            assert "sliceId" in tp
            assert "deviceId" in tp
            assert "metrics" in tp
            m = tp["metrics"]
            assert "packetRate" in m
            assert "throughput" in m
            assert "latency" in m
            assert "jitter" in m
            assert "lossRate" in m
            assert "anomalyScore" in tp
            assert tp["verdict"] in ("benign", "attack", "uncertain")

        # 5. Ping / Pong
        ws.send_text(json.dumps({"action": "PING"}))
        pong_raw = ws.receive_text()
        pong_msg = json.loads(pong_raw)
        # It may be another telemetry message or pong
        while pong_msg.get("type") != "pong":
            pong_raw = ws.receive_text()
            pong_msg = json.loads(pong_raw)
        assert pong_msg["type"] == "pong"
        assert "timestamp" in pong_msg


def test_twin_v2_subscribe_compat():
    """Verify /api/twin/ws also handles subscribe messages gracefully."""
    with client.websocket_connect("/api/twin/ws") as ws:
        init_raw = ws.receive_text()
        init_msg = json.loads(init_raw)
        assert init_msg["event_type"] == "INITIAL_SNAPSHOT"

        # Send subscribe message
        ws.send_text(json.dumps({
            "type": "subscribe",
            "payload": {
                "slices": ["sst-1-sd-010203"],
                "devices": ["ue-cam-01"],
                "metrics": ["packetRate"],
            },
        }))
        resp_raw = ws.receive_text()
        resp = json.loads(resp_raw)
        assert resp["type"] == "subscribed" or resp["event_type"] == "SUBSCRIBED"
# CommShield AI Core
