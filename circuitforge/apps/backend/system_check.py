"""
CircuitForge AI - System Detection
Detects OS, tools, and model availability. Reports actual state, never fabricated.
"""
from __future__ import annotations
import asyncio
import os
import platform
import shutil
import subprocess
from pathlib import Path
from typing import Optional
import httpx


def _arduino_env() -> dict:
    env = os.environ.copy()
    arduino_dir = Path(__file__).resolve().parent.parent.parent.parent / ".arduino15"
    arduino_dir.mkdir(parents=True, exist_ok=True)
    env["ARDUINO_DIRECTORIES_DATA"] = str(arduino_dir)
    env["ARDUINO_DIRECTORIES_USER"] = str(arduino_dir / "user")
    env["ARDUINO_DIRECTORIES_DOWNLOADS"] = str(arduino_dir / "staging")
    return env


async def check_ollama() -> dict:
    """Check if Ollama is running and reachable."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get("http://localhost:11434/api/version")
            if resp.status_code == 200:
                data = resp.json()
                return {"available": True, "version": data.get("version", "unknown"), "url": "http://localhost:11434"}
    except Exception as e:
        pass
    return {"available": False, "version": None, "url": "http://localhost:11434", "error": "Ollama not running or not reachable"}


async def list_ollama_models() -> list[dict]:
    """List installed Ollama models."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get("http://localhost:11434/api/tags")
            if resp.status_code == 200:
                data = resp.json()
                return data.get("models", [])
    except Exception:
        pass
    return []


async def check_model(model_name: str) -> dict:
    """Check if a specific model is installed and can perform inference."""
    models = await list_ollama_models()
    installed_names = [m.get("name", "") for m in models]

    # Fuzzy match: check if the model name appears in any installed model
    found = None
    for name in installed_names:
        if model_name.lower() in name.lower() or name.lower() in model_name.lower():
            found = name
            break

    if found is None:
        return {
            "name": model_name,
            "installed": False,
            "inference_ok": False,
            "error": f"Model '{model_name}' not found. Installed: {installed_names}"
        }

    # Quick inference test
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                "http://localhost:11434/api/generate",
                json={"model": found, "prompt": "Say OK", "stream": False, "options": {"num_predict": 5}}
            )
            if resp.status_code == 200:
                return {"name": found, "installed": True, "inference_ok": True}
            else:
                return {"name": found, "installed": True, "inference_ok": False, "error": f"HTTP {resp.status_code}"}
    except Exception as e:
        return {"name": found, "installed": True, "inference_ok": False, "error": str(e)}


def check_arduino_cli() -> dict:
    """Check if Arduino CLI is installed and functional."""
    path = shutil.which("arduino-cli")
    if path is None:
        return {"available": False, "path": None, "version": None,
                "error": "arduino-cli not found in PATH"}
    try:
        result = subprocess.run(
            ["arduino-cli", "version"],
            capture_output=True, text=True, timeout=10,
            env=_arduino_env(),
        )
        if result.returncode == 0:
            version = result.stdout.strip()
            return {"available": True, "path": path, "version": version}
        else:
            return {"available": False, "path": path, "version": None,
                    "error": result.stderr.strip()}
    except subprocess.TimeoutExpired:
        return {"available": False, "path": path, "version": None, "error": "arduino-cli version timed out"}
    except Exception as e:
        return {"available": False, "path": path, "version": None, "error": str(e)}


def check_wokwi_cli() -> dict:
    """Check if Wokwi CLI is installed."""
    path = shutil.which("wokwi-cli")
    if path is None:
        return {"available": False, "path": None, "version": None,
                "error": "wokwi-cli not found. Install from https://docs.wokwi.com/wokwi-ci/cli-usage"}
    try:
        result = subprocess.run(
            ["wokwi-cli", "--version"],
            capture_output=True, text=True, timeout=10,
        )
        version = result.stdout.strip() or result.stderr.strip()
        return {"available": True, "path": path, "version": version}
    except Exception as e:
        return {"available": False, "path": path, "version": None, "error": str(e)}


def check_arduino_boards() -> dict:
    """Check if ESP32 board core is installed."""
    try:
        result = subprocess.run(
            ["arduino-cli", "board", "listall"],
            capture_output=True, text=True, timeout=30,
            env=_arduino_env(),
        )
        if result.returncode == 0:
            has_esp32 = "esp32" in result.stdout.lower()
            return {"available": True, "esp32_installed": has_esp32,
                    "note": "ESP32 core found" if has_esp32 else "ESP32 core not installed. Run: arduino-cli core install esp32:esp32"}
        return {"available": False, "esp32_installed": False, "error": result.stderr.strip()}
    except Exception as e:
        return {"available": False, "esp32_installed": False, "error": str(e)}


async def get_system_status() -> dict:
    """Aggregate all system checks."""
    ollama = await check_ollama()
    arduino = check_arduino_cli()
    wokwi = check_wokwi_cli()

    models_info: dict = {}
    if ollama["available"]:
        planner = await check_model("gemma3:1b")
        firmware_gen = await check_model("Arduino-Coder")
        models_info = {"planner": planner, "firmware_generator": firmware_gen}
    else:
        models_info = {
            "planner": {"name": "gemma3:1b", "installed": False, "inference_ok": False, "error": "Ollama not running"},
            "firmware_generator": {"name": "hf.co/tapariapurv/Arduino-Coder-0.5B-GGUF-v1:Q4_K_M", "installed": False, "inference_ok": False, "error": "Ollama not running"},
        }

    boards_info = {}
    if arduino["available"]:
        boards_info = check_arduino_boards()

    return {
        "os": platform.system(),
        "arch": platform.machine(),
        "python": platform.python_version(),
        "ollama": ollama,
        "models": models_info,
        "arduino_cli": arduino,
        "arduino_boards": boards_info,
        "wokwi_cli": wokwi,
    }
