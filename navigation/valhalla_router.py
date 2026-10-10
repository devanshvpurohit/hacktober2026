"""
navigation/valhalla_router.py — Valhalla pedestrian routing for SURDAS.

Runs 100% in-process via the pyvalhalla Python bindings.
No Docker, no HTTP server, no background process.

Install once:
    pip install pyvalhalla

Build tiles once:
    python navigation/setup_valhalla.py --place Hyderabad

Then routing happens in-process at ~50–200 ms per route.

Fallback chain (automatic):
  1. pyvalhalla Actor (in-process)    ← fastest, preferred
  2. Valhalla HTTP server             ← if someone runs a server on :8002
  3. OfflineRouter (osmnx/NetworkX)  ← handled by Navigator, not here

Reference: https://github.com/valhalla/valhalla
"""
from __future__ import annotations

import json
import math
import os
import urllib.request
import urllib.error
from pathlib import Path
from typing import Optional

from navigation.router import TurnType, _haversine_m
from navigation.config import WALK_SPEED_MPS

# ── Tile paths ────────────────────────────────────────────────────────────────
_NAV_DIR   = Path(__file__).parent
TILES_DIR  = _NAV_DIR / "data" / "valhalla_tiles"
TILES_TAR  = TILES_DIR / "valhalla_tiles.tar"
CONFIG_FILE = TILES_DIR / "valhalla.json"

# HTTP server fallback (only used if pyvalhalla is not installed)
VALHALLA_HTTP_URL = os.getenv("VALHALLA_URL", "http://localhost:8002")


# ── Valhalla maneuver type → TurnType mapping ────────────────────────────────
# Full type list: https://valhalla.github.io/valhalla/api/turn-by-turn/api-reference/

_MANEUVER_MAP: dict[int, TurnType] = {
    0:  TurnType.DEPART,
    1:  TurnType.DEPART,
    2:  TurnType.DEPART,
    3:  TurnType.DEPART,
    4:  TurnType.ARRIVAL,
    5:  TurnType.ARRIVAL,
    6:  TurnType.ARRIVAL,
    7:  TurnType.SLIGHT_LEFT,
    8:  TurnType.STRAIGHT,
    9:  TurnType.SLIGHT_RIGHT,
    10: TurnType.RIGHT,
    11: TurnType.SHARP_RIGHT,
    12: TurnType.U_TURN,
    13: TurnType.U_TURN,
    14: TurnType.SHARP_LEFT,
    15: TurnType.LEFT,
    16: TurnType.SLIGHT_LEFT,
    17: TurnType.STRAIGHT,   # merge
    18: TurnType.STRAIGHT,   # roundabout enter
    19: TurnType.STRAIGHT,   # roundabout exit
    20: TurnType.STRAIGHT,   # ferry
    21: TurnType.STRAIGHT,
    29: TurnType.STRAIGHT,   # merge right
    30: TurnType.STRAIGHT,   # merge left
}


def _valhalla_turn(t: int) -> TurnType:
    return _MANEUVER_MAP.get(t, TurnType.STRAIGHT)


def _is_crossing(maneuver: dict) -> bool:
    verbal = maneuver.get("verbal_pre_transition_instruction", "").lower()
    return "cross" in verbal or "crossing" in verbal


def _extract_street(maneuver: dict) -> str:
    names = maneuver.get("street_names") or maneuver.get("begin_street_names") or []
    if names:
        first = names[0]
        if isinstance(first, dict):
            return first.get("value", "") or ""
        return str(first)
    return ""


# ── Polyline decoder (Valhalla uses precision=6) ──────────────────────────────

def _decode_polyline(encoded: str, precision: int = 6) -> list[list[float]]:
    factor = 10 ** precision
    coords: list[list[float]] = []
    index = lat = lng = 0
    while index < len(encoded):
        result = shift = 0
        while True:
            b = ord(encoded[index]) - 63
            index += 1
            result |= (b & 0x1F) << shift
            shift += 5
            if b < 0x20:
                break
        lat += (~(result >> 1) if result & 1 else result >> 1)
        result = shift = 0
        while True:
            b = ord(encoded[index]) - 63
            index += 1
            result |= (b & 0x1F) << shift
            shift += 5
            if b < 0x20:
                break
        lng += (~(result >> 1) if result & 1 else result >> 1)
        coords.append([lat / factor, lng / factor])
    return coords


# ── Shared maneuver → step conversion ─────────────────────────────────────────

def _maneuvers_to_steps(
    maneuvers: list[dict],
    coordinates: list[list[float]],
) -> list[dict]:
    steps = []
    for m in maneuvers:
        turn    = _valhalla_turn(int(m.get("type", 8)))
        dist_m  = float(m.get("length", 0.0)) * 1000.0   # km → m
        street  = _extract_street(m)
        is_cross = _is_crossing(m)
        verbal  = (
            m.get("verbal_pre_transition_instruction")
            or m.get("instruction", "")
        )
        shape_idx = int(m.get("begin_shape_index", 0))
        coord = coordinates[shape_idx] if shape_idx < len(coordinates) else [0.0, 0.0]
        steps.append({
            "turn":        turn,
            "distance_m":  round(dist_m, 1),
            "street_name": street,
            "is_crossing": is_cross,
            "start_coord": coord,
            "instruction": verbal,
        })
    return steps


# ── Standard Valhalla request payload ────────────────────────────────────────

def _make_request(
    start_lat: float, start_lon: float,
    dest_lat: float,  dest_lon: float,
) -> dict:
    return {
        "locations": [
            {"lat": start_lat, "lon": start_lon, "type": "break"},
            {"lat": dest_lat,  "lon": dest_lon,  "type": "break"},
        ],
        "costing": "pedestrian",
        "costing_options": {
            "pedestrian": {
                "walking_speed":   WALK_SPEED_MPS * 3.6,
                "use_roads":       0.5,
                "use_sidewalks":   1.0,
                "use_living_streets": 0.8,
                "use_tracks":      0.3,
            }
        },
        "directions_options": {
            "units":    "kilometers",
            "language": "en-US",
        },
        "narrative": True,
    }


def _parse_response(raw: dict) -> dict:
    """Convert a Valhalla /route JSON response into a SURDAS route dict."""
    try:
        leg     = raw["trip"]["legs"][0]
        summary = raw["trip"]["summary"]
    except (KeyError, IndexError):
        raise ValueError("Unexpected Valhalla response format.")

    distance_m  = summary["length"] * 1000.0
    duration_s  = summary["time"]
    coordinates = _decode_polyline(leg["shape"])
    steps       = _maneuvers_to_steps(leg.get("maneuvers", []), coordinates)

    return {
        "distance_m":  round(distance_m, 1),
        "duration_s":  round(duration_s, 0),
        "coordinates": coordinates,
        "steps":       steps,
        "source":      "valhalla",
    }


# ── In-process Actor backend (pyvalhalla) ─────────────────────────────────────

class _ActorBackend:
    """
    Uses pyvalhalla's Actor class to route entirely in-process.
    No server, no Docker, no network calls.
    """

    def __init__(self):
        from valhalla import Actor, get_config  # type: ignore[import]

        # Prefer a pre-built tar (compact), fall back to directory
        if TILES_TAR.exists():
            config = get_config(tile_extract=str(TILES_TAR), verbose=False)
        elif TILES_DIR.exists() and any(TILES_DIR.iterdir()):
            config = get_config(tile_dir=str(TILES_DIR), verbose=False)
        elif CONFIG_FILE.exists():
            config = json.loads(CONFIG_FILE.read_text())
        else:
            raise FileNotFoundError(
                f"No Valhalla tiles found in {TILES_DIR}.\n"
                "Run: python navigation/setup_valhalla.py --place Hyderabad"
            )

        self._actor = Actor(config)
        print(f"[VALHALLA] In-process Actor loaded tiles from {TILES_DIR}")

    def route(self, request: dict) -> dict:
        raw = self._actor.route(request)   # returns a dict directly
        if isinstance(raw, str):
            raw = json.loads(raw)
        return _parse_response(raw)

    @staticmethod
    def is_available() -> bool:
        try:
            import valhalla  # type: ignore[import]  # noqa: F401
            return (
                TILES_TAR.exists()
                or (TILES_DIR.exists() and any(TILES_DIR.iterdir()))
                or CONFIG_FILE.exists()
            )
        except ImportError:
            return False


# ── HTTP fallback backend (existing server) ────────────────────────────────────

class _HttpBackend:
    """Calls a Valhalla HTTP server — used only when pyvalhalla is absent."""

    def __init__(self, base_url: str = VALHALLA_HTTP_URL):
        self._base_url = base_url.rstrip("/")

    def route(self, request: dict) -> dict:
        data = json.dumps(request).encode()
        req = urllib.request.Request(
            f"{self._base_url}/route",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=5.0) as resp:
                raw = json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            if e.code == 442 or "No path" in body:
                raise ValueError("Valhalla found no pedestrian route.")
            raise RuntimeError(f"Valhalla HTTP {e.code}: {body[:200]}")
        except (urllib.error.URLError, OSError) as e:
            raise RuntimeError(
                f"Valhalla HTTP server unreachable at {self._base_url}.\n"
                f"Install pyvalhalla instead: pip install pyvalhalla"
            )
        return _parse_response(raw)

    def is_available(self) -> bool:
        try:
            with urllib.request.urlopen(
                f"{self._base_url}/status", timeout=2.0
            ) as resp:
                return resp.status == 200
        except Exception:
            return False


# ── Public ValhallaRouter ──────────────────────────────────────────────────────

class ValhallaRouter:
    """
    Pedestrian route calculator using Valhalla — no Docker, no server.

    Backend selection (automatic):
      1. pyvalhalla Actor (in-process)  — if `pip install pyvalhalla` + tiles built
      2. HTTP server on localhost:8002  — if someone runs a Valhalla server
      3. Raises RuntimeError           — caller (Navigator) falls back to OfflineRouter

    Same .route() interface as OfflineRouter — drop-in replacement.
    """

    def __init__(self):
        self._backend: Optional[_ActorBackend | _HttpBackend] = None
        self._mode: str = "none"
        self._init_backend()

    def _init_backend(self) -> None:
        # Try in-process first (fastest, no external dependency at runtime)
        if _ActorBackend.is_available():
            try:
                self._backend = _ActorBackend()
                self._mode = "actor"
                return
            except Exception as e:
                print(f"[VALHALLA] Actor init failed ({e}) — trying HTTP fallback.")

        # Try HTTP server as fallback
        http_b = _HttpBackend()
        if http_b.is_available():
            self._backend = http_b
            self._mode = "http"
            print("[VALHALLA] Using HTTP server fallback (localhost:8002).")
            return

        # Nothing available
        self._mode = "none"

    def is_available(self) -> bool:
        return self._mode in ("actor", "http")

    @property
    def mode(self) -> str:
        """Returns 'actor', 'http', or 'none'."""
        return self._mode

    def route(
        self,
        start_lat: float,
        start_lon: float,
        dest_lat: float,
        dest_lon: float,
    ) -> dict:
        """
        Calculate pedestrian route. Returns same dict as OfflineRouter.route().

        Raises:
            RuntimeError  if no backend is available
            ValueError    if no route exists between the points
        """
        if self._backend is None:
            raise RuntimeError(
                "Valhalla is not available.\n"
                "Install: pip install pyvalhalla\n"
                "Build tiles: python navigation/setup_valhalla.py --place Hyderabad"
            )
        request = _make_request(start_lat, start_lon, dest_lat, dest_lon)
        return self._backend.route(request)


# ── Quick availability check ───────────────────────────────────────────────────

def valhalla_available() -> bool:
    """True if pyvalhalla is installed AND tiles exist, OR an HTTP server is up."""
    return ValhallaRouter().is_available()
