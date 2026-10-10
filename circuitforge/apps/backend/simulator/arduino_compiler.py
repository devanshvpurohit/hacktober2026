"""
CircuitForge AI - Arduino CLI Integration
Handles actual firmware compilation, board core checks, and library verification.
Uses safe subprocess argument lists — no shell interpolation of user input.
"""
from __future__ import annotations
import asyncio
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional

COMPILE_TIMEOUT = 120  # seconds
MAX_OUTPUT_BYTES = 1024 * 512  # 512 KB

ESP32_FQBN = "esp32:esp32:esp32"


def _arduino_env() -> dict:
    env = os.environ.copy()
    arduino_dir = Path(__file__).resolve().parent.parent.parent.parent / ".arduino15"
    arduino_dir.mkdir(parents=True, exist_ok=True)
    env["ARDUINO_DIRECTORIES_DATA"] = str(arduino_dir)
    env["ARDUINO_DIRECTORIES_USER"] = str(arduino_dir / "user")
    env["ARDUINO_DIRECTORIES_DOWNLOADS"] = str(arduino_dir / "staging")
    return env


def _arduino_cli_path() -> Optional[str]:
    path = shutil.which("arduino-cli")
    if path:
        return path
    for candidate in [
        "/opt/homebrew/bin/arduino-cli",
        "/usr/local/bin/arduino-cli",
        str(Path.home() / ".local/bin/arduino-cli"),
    ]:
        if os.path.exists(candidate) and os.access(candidate, os.X_OK):
            return candidate
    return None


def arduino_cli_available() -> bool:
    return _arduino_cli_path() is not None


def check_esp32_core() -> dict:
    """Check if esp32:esp32 core is installed."""
    path = _arduino_cli_path()
    if not path:
        return {"installed": False, "error": "arduino-cli not found"}
    try:
        result = subprocess.run(
            [path, "core", "list"],
            capture_output=True, text=True, timeout=30,
            env=_arduino_env(),
        )
        has_esp32 = "esp32:esp32" in result.stdout
        return {
            "installed": has_esp32,
            "stdout": result.stdout[:2000],
            "note": "ESP32 core found" if has_esp32 else
                    "Run: arduino-cli core install esp32:esp32"
        }
    except subprocess.TimeoutExpired:
        return {"installed": False, "error": "Core check timed out"}
    except Exception as e:
        return {"installed": False, "error": str(e)}


async def compile_firmware(sketch_dir: Path, project_name: str) -> dict:
    """
    Compile an Arduino sketch using Arduino CLI.
    sketch_dir: directory containing sketch.ino
    project_name: used for the .ino filename

    Returns dict with keys: success, exit_code, stdout, stderr, binary_path
    """
    path = _arduino_cli_path()
    if not path:
        return {
            "success": False, "exit_code": -1,
            "stdout": "", "stderr": "arduino-cli not found",
            "binary_path": None,
        }

    sketch_file = sketch_dir / "sketch.ino"
    if not sketch_file.exists():
        return {
            "success": False, "exit_code": -1,
            "stdout": "", "stderr": f"sketch.ino not found at {sketch_file}",
            "binary_path": None,
        }

    # Arduino CLI compiles all .ino files in a directory together.
    # To avoid redefinition when both sketch.ino and <dir>.ino exist, create a clean
    # temporary build sketch dir if needed, or pass the sketch.ino file directly.
    import tempfile
    with tempfile.TemporaryDirectory() as compile_tmp:
        tmp_sketch_dir = Path(compile_tmp) / "sketch"
        tmp_sketch_dir.mkdir()
        shutil.copy2(sketch_file, tmp_sketch_dir / "sketch.ino")

        build_dir = sketch_dir / "build"
        build_dir.mkdir(exist_ok=True)

        cmd = [
            path, "compile",
            "--fqbn", ESP32_FQBN,
            "--build-path", str(build_dir.resolve()),
            "--warnings", "default",
            "--additional-urls", "https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json",
            str(tmp_sketch_dir),
        ]

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(tmp_sketch_dir),
                env=_arduino_env(),
            )

            try:
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    proc.communicate(), timeout=COMPILE_TIMEOUT
                )
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
                return {
                    "success": False, "exit_code": -1,
                    "stdout": "", "stderr": f"Compilation timed out after {COMPILE_TIMEOUT}s",
                    "binary_path": None,
                }

            stdout = stdout_bytes[:MAX_OUTPUT_BYTES].decode("utf-8", errors="replace")
            stderr = stderr_bytes[:MAX_OUTPUT_BYTES].decode("utf-8", errors="replace")
            exit_code = proc.returncode

            binary_path = None
            if exit_code == 0:
                for ext in [".bin", ".elf"]:
                    for f in build_dir.rglob(f"*{ext}"):
                        binary_path = str(f)
                        break
                    if binary_path:
                        break

            return {
                "success": exit_code == 0,
                "exit_code": exit_code,
                "stdout": stdout,
                "stderr": stderr,
                "binary_path": binary_path,
            }

        except Exception as e:
            return {
                "success": False, "exit_code": -1,
                "stdout": "", "stderr": f"Subprocess error: {e}",
                "binary_path": None,
            }


async def check_library(library_name: str) -> bool:
    """Check if a library is installed in Arduino CLI."""
    path = _arduino_cli_path()
    if not path:
        return False
    try:
        result = subprocess.run(
            [path, "lib", "list"],
            capture_output=True, text=True, timeout=15,
            env=_arduino_env(),
        )
        return library_name.lower() in result.stdout.lower()
    except Exception:
        return False


async def install_library(library_name: str) -> dict:
    """Install a library via Arduino CLI."""
    path = _arduino_cli_path()
    if not path:
        return {"success": False, "error": "arduino-cli not found"}
    try:
        result = subprocess.run(
            [path, "lib", "install", library_name],
            capture_output=True, text=True, timeout=60,
            env=_arduino_env(),
        )
        return {
            "success": result.returncode == 0,
            "stdout": result.stdout[:5000],
            "stderr": result.stderr[:5000],
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Library install timed out"}
    except Exception as e:
        return {"success": False, "error": str(e)}
