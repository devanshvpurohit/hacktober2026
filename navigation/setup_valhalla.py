#!/usr/bin/env python3
"""
navigation/setup_valhalla.py — One-time Valhalla tile builder for SURDAS.

No Docker required. Uses pyvalhalla's bundled CLI tools to download an OSM
PBF and build routing tiles entirely in Python.

Usage:
    python navigation/setup_valhalla.py --place Hyderabad
    python navigation/setup_valhalla.py --place Mumbai
    python navigation/setup_valhalla.py --status
    python navigation/setup_valhalla.py --clean   # delete tiles and start over

Requirements (install once):
    pip install pyvalhalla requests tqdm

Reference:
    https://github.com/valhalla/valhalla
    https://pypi.org/project/pyvalhalla/
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import urllib.request
from pathlib import Path


# ── Paths ─────────────────────────────────────────────────────────────────────
_NAV_DIR   = Path(__file__).parent
TILES_DIR  = _NAV_DIR / "data" / "valhalla_tiles"
PBF_DIR    = _NAV_DIR / "data" / "pbf"
CONFIG_FILE = TILES_DIR / "valhalla.json"
TILES_TAR  = TILES_DIR / "valhalla_tiles.tar"

# Geofabrik PBF URLs for Indian cities/states
GEOFABRIK: dict[str, str] = {
    "hyderabad":   "https://download.geofabrik.de/asia/india/telangana-latest.osm.pbf",
    "telangana":   "https://download.geofabrik.de/asia/india/telangana-latest.osm.pbf",
    "mumbai":      "https://download.geofabrik.de/asia/india/maharashtra-latest.osm.pbf",
    "maharashtra": "https://download.geofabrik.de/asia/india/maharashtra-latest.osm.pbf",
    "delhi":       "https://download.geofabrik.de/asia/india-latest.osm.pbf",
    "bangalore":   "https://download.geofabrik.de/asia/india/karnataka-latest.osm.pbf",
    "karnataka":   "https://download.geofabrik.de/asia/india/karnataka-latest.osm.pbf",
    "chennai":     "https://download.geofabrik.de/asia/india/tamil-nadu-latest.osm.pbf",
    "tamilnadu":   "https://download.geofabrik.de/asia/india/tamil-nadu-latest.osm.pbf",
    "pune":        "https://download.geofabrik.de/asia/india/maharashtra-latest.osm.pbf",
    "kolkata":     "https://download.geofabrik.de/asia/india/west-bengal-latest.osm.pbf",
    "india":       "https://download.geofabrik.de/asia/india-latest.osm.pbf",
}


# ── Dependency check ──────────────────────────────────────────────────────────

def _check_pyvalhalla() -> bool:
    try:
        import valhalla  # noqa: F401
        return True
    except ImportError:
        return False


def _require_pyvalhalla() -> None:
    if not _check_pyvalhalla():
        print("\n[ERROR] pyvalhalla is not installed.")
        print("Install it with:\n")
        print("    pip install pyvalhalla\n")
        print("pyvalhalla includes Valhalla's C++ engine + build tools.")
        print("No Docker or system packages required.")
        sys.exit(1)


# ── PBF download ──────────────────────────────────────────────────────────────

def _resolve_pbf_url(place: str) -> str:
    place_lower = place.lower().replace(" ", "").replace("-", "")
    if place_lower in GEOFABRIK:
        return GEOFABRIK[place_lower]
    for key, url in GEOFABRIK.items():
        if key in place_lower or place_lower in key:
            return url
    print(f"[ERROR] No Geofabrik URL for '{place}'.")
    print("Available places:", ", ".join(GEOFABRIK.keys()))
    print("Or provide a custom URL with --pbf-url <url>")
    sys.exit(1)


def _download_pbf(url: str, dest: Path) -> None:
    """Download PBF with a progress bar (uses requests+tqdm if available)."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    print(f"\n[DOWNLOAD] {url}")
    print(f"[DOWNLOAD] → {dest}")
    try:
        import requests  # type: ignore
        from tqdm import tqdm  # type: ignore
        r = requests.get(url, stream=True, timeout=60)
        r.raise_for_status()
        total = int(r.headers.get("content-length", 0))
        with open(dest, "wb") as f, tqdm(
            total=total, unit="B", unit_scale=True, desc=dest.name
        ) as bar:
            for chunk in r.iter_content(chunk_size=65536):
                f.write(chunk)
                bar.update(len(chunk))
    except ImportError:
        print("[DOWNLOAD] (install requests+tqdm for a progress bar)")
        urllib.request.urlretrieve(url, dest)
    print(f"[DOWNLOAD] ✅  {dest.stat().st_size / 1_000_000:.1f} MB saved")


# ── Valhalla config generation ────────────────────────────────────────────────

def _generate_config() -> dict:
    """
    Build a minimal Valhalla JSON config pointing at our tiles directory.
    Uses pyvalhalla.get_config() if available, otherwise handcrafts one.
    """
    try:
        from valhalla import get_config  # type: ignore
        # Prefer a tar if it already exists, otherwise use directory
        if TILES_TAR.exists():
            cfg = get_config(tile_extract=str(TILES_TAR), verbose=False)
        else:
            cfg = get_config(tile_dir=str(TILES_DIR), verbose=False)
        return cfg
    except (ImportError, Exception):
        # Minimal handcrafted config
        return {
            "mjolnir": {
                "tile_dir":     str(TILES_DIR),
                "tile_extract": str(TILES_TAR) if TILES_TAR.exists() else "",
                "timezone":     str(TILES_DIR / "tz_world.sqlite"),
                "admin":        str(TILES_DIR / "admins.sqlite"),
            },
            "loki":   {"logging": {"type": "std_err", "color": False, "file_name": ""}},
            "thor":   {"logging": {"type": "std_err", "color": False, "file_name": ""}},
            "odin":   {"logging": {"type": "std_err", "color": False, "file_name": ""}},
            "meili":  {"logging": {"type": "std_err", "color": False, "file_name": ""}},
            "service_limits": {
                "pedestrian": {
                    "max_distance": 200000,
                    "max_locations": 50,
                    "max_matrix_distance": 200000,
                    "max_matrix_location_pairs": 2500,
                },
            },
        }


def _run_valhalla_tool(tool: str, *args: str) -> int:
    """
    Run a Valhalla CLI tool via pyvalhalla's bundled binaries.
    pyvalhalla ships executables runnable as:  python -m valhalla <tool> <args>
    """
    cmd = [sys.executable, "-m", "valhalla", tool, *args]
    print(f"\n$ {' '.join(cmd)}\n")
    result = subprocess.run(cmd)
    return result.returncode


# ── Tile build ────────────────────────────────────────────────────────────────

def cmd_build(place: str, pbf_url: str | None) -> None:
    _require_pyvalhalla()

    url = pbf_url or _resolve_pbf_url(place)
    pbf_name = url.split("/")[-1]
    pbf_path = PBF_DIR / pbf_name

    # 1. Download PBF
    if pbf_path.exists():
        print(f"[SKIP] PBF already exists: {pbf_path}")
    else:
        _download_pbf(url, pbf_path)

    # 2. Prepare directories
    TILES_DIR.mkdir(parents=True, exist_ok=True)

    # 3. Generate config
    print("\n[CONFIG] Generating valhalla.json ...")
    cfg = _generate_config()
    # Override tile_dir to our location
    cfg.setdefault("mjolnir", {})["tile_dir"] = str(TILES_DIR)
    CONFIG_FILE.write_text(json.dumps(cfg, indent=2))
    print(f"[CONFIG] ✅  Written to {CONFIG_FILE}")

    # 4. Build tiles using pyvalhalla's bundled valhalla_build_tiles
    print(f"\n[TILES] Building routing tiles from {pbf_name} ...")
    print("[TILES] This takes 2–15 minutes depending on area size.\n")

    rc = _run_valhalla_tool(
        "valhalla_build_tiles",
        "-c", str(CONFIG_FILE),
        str(pbf_path),
    )

    if rc != 0:
        print(f"\n[ERROR] valhalla_build_tiles exited with code {rc}")
        print("Try: pip install --upgrade pyvalhalla")
        sys.exit(rc)

    print("\n[TILES] ✅  Tiles built successfully.")

    # 5. Optionally pack tiles into a tar for faster Actor startup
    print("\n[TAR] Packing tiles into valhalla_tiles.tar ...")
    rc2 = _run_valhalla_tool(
        "valhalla_pack_tiles",
        "-c", str(CONFIG_FILE),
        "-i", str(TILES_DIR),
        "-o", str(TILES_TAR),
    )
    if rc2 == 0:
        print(f"[TAR] ✅  {TILES_TAR} ({TILES_TAR.stat().st_size / 1_000_000:.1f} MB)")
    else:
        print("[TAR] ⚠️  valhalla_pack_tiles failed — tiles directory will be used instead.")

    # 6. Verify
    print("\n[VERIFY] Testing routing engine ...")
    _verify()

    print("\n" + "=" * 60)
    print("  VALHALLA READY — no Docker required!")
    print("  Run SURDAS normally:")
    print("  python surdas_brain.py")
    print("=" * 60 + "\n")


# ── Status ────────────────────────────────────────────────────────────────────

def cmd_status() -> None:
    pv = _check_pyvalhalla()
    tiles_ok = TILES_TAR.exists() or (
        TILES_DIR.exists() and any(
            f.suffix not in (".pbf", ".json") for f in TILES_DIR.iterdir()
        )
    )
    config_ok = CONFIG_FILE.exists()

    # Try instantiating the Actor
    actor_ok = False
    if pv and tiles_ok:
        try:
            from navigation.valhalla_router import ValhallaRouter
            vr = ValhallaRouter()
            actor_ok = vr.is_available()
        except Exception:
            pass

    print("\n── Valhalla Status (no Docker) ───────────────────────────")
    print(f"  pyvalhalla installed : {'✅' if pv else '❌  (pip install pyvalhalla)'}")
    print(f"  Tiles directory      : {TILES_DIR}")
    print(f"  Tiles exist          : {'✅' if tiles_ok else '❌  (run --place <city>)'}")
    print(f"  Tiles tar            : {'✅' if TILES_TAR.exists() else '—'}")
    print(f"  Config file          : {'✅' if config_ok else '—'}")
    print(f"  Actor ready          : {'✅' if actor_ok else '❌'}")
    print("──────────────────────────────────────────────────────────\n")

    if not pv:
        print("  To install pyvalhalla:")
        print("    pip install pyvalhalla\n")
    if not tiles_ok:
        print("  To build tiles:")
        print("    python navigation/setup_valhalla.py --place Hyderabad\n")


# ── Clean ─────────────────────────────────────────────────────────────────────

def cmd_clean() -> None:
    import shutil
    if TILES_DIR.exists():
        answer = input(f"Delete {TILES_DIR} and all tiles? [y/N] ").strip().lower()
        if answer == "y":
            shutil.rmtree(TILES_DIR)
            print(f"[CLEAN] ✅  Deleted {TILES_DIR}")
        else:
            print("[CLEAN] Aborted.")
    else:
        print(f"[CLEAN] {TILES_DIR} does not exist.")


# ── Quick verify ──────────────────────────────────────────────────────────────

def _verify() -> None:
    """Run a tiny test route to confirm the Actor works."""
    try:
        from navigation.valhalla_router import ValhallaRouter
        vr = ValhallaRouter()
        if not vr.is_available():
            print("[VERIFY] ⚠️  ValhallaRouter not available after build.")
            return
        # Short test route within Hyderabad
        result = vr.route(17.3850, 78.4867, 17.3900, 78.4910)
        dist = result["distance_m"]
        steps = len(result["steps"])
        print(f"[VERIFY] ✅  Test route: {dist:.0f} m, {steps} steps, engine={result['source']}")
    except Exception as e:
        print(f"[VERIFY] ⚠️  Test route failed: {e}")
        print("[VERIFY] This may be normal if tiles don't cover the test coordinates.")


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Set up Valhalla routing for SURDAS — no Docker required.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Quick start:
  pip install pyvalhalla
  python navigation/setup_valhalla.py --place Hyderabad
  python surdas_brain.py

Examples:
  python navigation/setup_valhalla.py --place Hyderabad
  python navigation/setup_valhalla.py --place Mumbai
  python navigation/setup_valhalla.py --place Delhi
  python navigation/setup_valhalla.py --place Bangalore
  python navigation/setup_valhalla.py --status
  python navigation/setup_valhalla.py --clean

Custom PBF URL (any region on Geofabrik):
  python navigation/setup_valhalla.py \\
      --place Custom \\
      --pbf-url https://download.geofabrik.de/asia/india/andhra-pradesh-latest.osm.pbf
        """
    )
    parser.add_argument("--place",   "-p", metavar="CITY",
                        help="City / region to build tiles for")
    parser.add_argument("--pbf-url", metavar="URL",
                        help="Custom Geofabrik .osm.pbf download URL")
    parser.add_argument("--status",  action="store_true",
                        help="Show current Valhalla setup status")
    parser.add_argument("--clean",   action="store_true",
                        help="Delete tiles and start fresh")
    args = parser.parse_args()

    if args.status:
        cmd_status()
    elif args.clean:
        cmd_clean()
    elif args.place:
        cmd_build(args.place, args.pbf_url)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
