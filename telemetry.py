import asyncio
import threading
import uvicorn
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import json
import urllib.request

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

connected_clients: set = set()
_loop = None
_started = False          # Guard: only start server once per process
_lock = threading.Lock()

# ──────────────────────────────────────────────────
# WebSocket endpoint
# ──────────────────────────────────────────────────
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connected_clients.add(websocket)
    try:
        while True:
            await websocket.receive_text()
    except Exception:
        connected_clients.discard(websocket)

# ──────────────────────────────────────────────────
# WiFi / Hardware GPS / Local Location
# ──────────────────────────────────────────────────
@app.get("/location")
def get_location():
    # 1. Try local DevKit GPS endpoint first (offline priority)
    try:
        req = urllib.request.Request("http://192.168.4.2/gps")
        with urllib.request.urlopen(req, timeout=0.5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if data.get("fix"):
                return {
                    "lat": float(data.get("latitude", 0.0)),
                    "lng": float(data.get("longitude", 0.0)),
                    "city": "GPS Fix",
                    "region": f"Sats: {data.get('satellites', 0)}",
                    "country": "India",
                    "org": "NEO-6M GPS",
                }
    except Exception:
        pass

    # 2. Try IP-based location with a fast 1s timeout if online
    try:
        req = urllib.request.Request(
            "http://ipinfo.io/json",
            headers={"User-Agent": "SURDAS/1.0"}
        )
        with urllib.request.urlopen(req, timeout=1.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if "loc" in data:
                lat, lng = data["loc"].split(",")
                return {
                    "lat": float(lat),
                    "lng": float(lng),
                    "city": data.get("city", "Unknown"),
                    "region": data.get("region", ""),
                    "country": data.get("country", ""),
                    "org": data.get("org", ""),
                }
    except Exception:
        pass

    # 3. Offline fallback (Hyderabad default)
    return {"lat": 17.3850, "lng": 78.4867, "city": "Hyderabad (Offline)", "region": "Telangana", "country": "India", "org": "SURDAS Offline"}

# ──────────────────────────────────────────────────
# Health check
# ──────────────────────────────────────────────────
@app.get("/health")
def health():
    return {"status": "ok", "clients": len(connected_clients)}

# ──────────────────────────────────────────────────
# Grab event loop on startup
# ──────────────────────────────────────────────────
@app.on_event("startup")
async def startup_event():
    global _loop
    _loop = asyncio.get_running_loop()
    print("[TELEMETRY] Dashboard server ready — ws://localhost:8000/ws")

# ──────────────────────────────────────────────────
# Broadcast from any thread (thread-safe)
# ──────────────────────────────────────────────────
def broadcast_event(event_type: str, payload: dict):
    """Send an event to all connected dashboard clients.
    Safe to call from any thread (main AI loop, TTS thread, etc.)."""
    if not _loop:
        return
    message = json.dumps({"type": event_type, "data": payload})

    async def _send():
        dead = set()
        for client in list(connected_clients):
            try:
                await client.send_text(message)
            except Exception:
                dead.add(client)
        connected_clients.difference_update(dead)

    asyncio.run_coroutine_threadsafe(_send(), _loop)

# ──────────────────────────────────────────────────
# Start server (singleton — safe to call from both
# surdas_brain.py AND test_ai_pipeline.py)
# ──────────────────────────────────────────────────
def start_telemetry(port: int = 8000):
    global _started
    with _lock:
        if _started:
            print("[TELEMETRY] Already running — skipping duplicate start.")
            return
        _started = True

    def _run():
        config = uvicorn.Config(
            app,
            host="0.0.0.0",
            port=port,
            log_level="error",
            # Disable uvicorn's default signal handlers so the main AI loop keeps control
            loop="none",
        )
        server = uvicorn.Server(config)
        # Run inside a fresh asyncio event loop for this background thread
        asyncio.run(server.serve())

    t = threading.Thread(target=_run, daemon=True, name="TelemetryServer")
    t.start()
    print(f"[TELEMETRY] Dashboard server starting on http://0.0.0.0:{port}")
