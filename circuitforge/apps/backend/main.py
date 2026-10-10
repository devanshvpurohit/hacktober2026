"""
CircuitForge AI - FastAPI Backend
Main application with all API endpoints.
Binds to 127.0.0.1 by default. Never sends data to cloud services.
"""
from __future__ import annotations
import asyncio
import json
import os
import sys
import time
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

# ── Path setup ────────────────────────────────────────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from schemas import (
    CreateProjectRequest, Project, ProjectSummary,
    ProjectStatus, SimulationStatus, RepairAttempt
)
from storage.db import (
    init_db, create_project, get_project, update_project,
    list_projects, delete_project, get_project_logs,
    log_operation, export_project_zip
)
from system_check import get_system_status, check_ollama, list_ollama_models
from catalog.components import CATALOG, list_components, search_components
from catalog.diagram_generator import generate_diagram
from catalog.bom_generator import generate_bom
from validators.project_validator import (
    validate_project_spec, validate_diagram, validate_firmware_pins, validate_zip_contents
)
from ai.ollama_client import plan_project, generate_firmware, repair_firmware
from simulator.arduino_compiler import (
    compile_firmware, arduino_cli_available, check_esp32_core
)


# ── App lifespan ──────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title="CircuitForge AI",
    description="Local-first AI-powered IoT builder",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173",
                   "http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Health / System ───────────────────────────────────────────────────────────

@app.get("/api/health")
async def health():
    ollama = await check_ollama()
    arduino = arduino_cli_available()
    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "ollama_running": ollama["available"],
        "arduino_cli_available": arduino,
    }


@app.get("/api/system")
async def system_status():
    return await get_system_status()


@app.get("/api/models")
async def models():
    ollama = await check_ollama()
    if not ollama["available"]:
        return {"ollama_running": False, "models": [], "error": ollama.get("error")}
    models_list = await list_ollama_models()
    return {"ollama_running": True, "models": models_list}


class InstallModelRequest(BaseModel):
    model_name: str


@app.post("/api/models/install")
async def install_model(req: InstallModelRequest):
    """
    Returns the ollama pull command for the user to run.
    We do not auto-download large models without explicit user action.
    """
    return {
        "message": f"To install model '{req.model_name}', run the following command in your terminal:",
        "command": f"ollama pull {req.model_name}",
        "note": "Large models require significant disk space. Ensure Ollama is running first with: ollama serve",
    }


# ── Catalog ───────────────────────────────────────────────────────────────────

@app.get("/api/catalog")
async def get_catalog():
    return [c.model_dump() for c in list_components()]


@app.get("/api/catalog/search")
async def search_catalog(q: str):
    return [c.model_dump() for c in search_components(q)]


# ── Projects ──────────────────────────────────────────────────────────────────

@app.get("/api/projects")
async def list_all_projects():
    projects = await list_projects()
    return [p.model_dump() for p in projects]


@app.post("/api/projects", status_code=201)
async def create_new_project(req: CreateProjectRequest):
    project = await create_project(req.user_request)
    return project.model_dump()


@app.get("/api/projects/{project_id}")
async def get_project_detail(project_id: str):
    _validate_project_id(project_id)
    project = await get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project.model_dump()


@app.delete("/api/projects/{project_id}")
async def delete_project_endpoint(project_id: str):
    _validate_project_id(project_id)
    deleted = await delete_project(project_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"deleted": True}


@app.get("/api/projects/{project_id}/logs")
async def project_logs(project_id: str):
    _validate_project_id(project_id)
    return await get_project_logs(project_id)


@app.get("/api/projects/{project_id}/bom")
async def project_bom(project_id: str):
    _validate_project_id(project_id)
    project = await get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.bom is None:
        raise HTTPException(status_code=404, detail="BOM not yet generated")
    return project.bom.model_dump()


@app.get("/api/projects/{project_id}/download")
async def download_project(project_id: str):
    _validate_project_id(project_id)
    project = await get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    zip_path = await export_project_zip(project_id)
    if zip_path is None:
        raise HTTPException(status_code=500, detail="Could not generate ZIP export")

    return FileResponse(
        path=zip_path,
        media_type="application/zip",
        filename=f"{project.name.replace(' ', '_')}_{project_id[:8]}.zip",
    )


# ── Plan ──────────────────────────────────────────────────────────────────────

@app.post("/api/projects/{project_id}/plan")
async def plan_project_endpoint(project_id: str):
    _validate_project_id(project_id)
    project = await get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    project.status = ProjectStatus.PLANNING
    await update_project(project)

    start = time.time()
    try:
        spec, raw = await plan_project(project.user_request)

        project.spec = spec
        project.name = spec.name
        project.description = spec.description
        project.status = ProjectStatus.PLANNED
        project.error_message = None

        # Generate BOM immediately after planning
        project.bom = generate_bom(project_id, spec)

        await update_project(project)
        await log_operation(
            project_id, "plan", "success",
            duration_ms=int((time.time() - start) * 1000),
            message=f"Planned with {len(spec.components)} components"
        )
        return project.model_dump()

    except ValueError as e:
        project.status = ProjectStatus.ERROR
        project.error_message = str(e)
        await update_project(project)
        await log_operation(project_id, "plan", "error", message=str(e))
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        project.status = ProjectStatus.ERROR
        project.error_message = f"Unexpected error during planning: {e}"
        await update_project(project)
        raise HTTPException(status_code=500, detail=str(e))


# ── Generate (diagram + firmware) ─────────────────────────────────────────────

@app.post("/api/projects/{project_id}/generate")
async def generate_project(project_id: str):
    _validate_project_id(project_id)
    project = await get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.spec is None:
        try:
            spec, raw = await plan_project(project.user_request)
            project.spec = spec
            project.name = spec.name
            project.description = spec.description
            project.bom = generate_bom(project_id, spec)
        except Exception as e:
            raise HTTPException(status_code=422, detail=f"Planning failed: {e}")

    project.status = ProjectStatus.GENERATING
    await update_project(project)
    start = time.time()

    try:
        # 1. Generate diagram (deterministic, no AI)
        diagram = generate_diagram(project.spec)
        diagram_validation = validate_diagram(diagram)
        project.diagram_json = diagram

        # 2. Generate firmware (AI)
        firmware, raw = await generate_firmware(project.spec)
        project.firmware_code = firmware

        project.status = ProjectStatus.GENERATED
        project.error_message = None
        await update_project(project)
        await log_operation(
            project_id, "generate", "success",
            duration_ms=int((time.time() - start) * 1000),
            message=f"Diagram: {len(diagram.get('parts', []))} parts. Firmware: {len(firmware)} chars."
        )
        return project.model_dump()

    except ValueError as e:
        project.status = ProjectStatus.ERROR
        project.error_message = str(e)
        await update_project(project)
        await log_operation(project_id, "generate", "error", message=str(e))
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        project.status = ProjectStatus.ERROR
        project.error_message = f"Generation error: {e}"
        await update_project(project)
        raise HTTPException(status_code=500, detail=str(e))


# ── Validate ──────────────────────────────────────────────────────────────────

@app.post("/api/projects/{project_id}/validate")
async def validate_project(project_id: str):
    _validate_project_id(project_id)
    project = await get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.spec is None:
        raise HTTPException(status_code=400, detail="No spec to validate")

    project.status = ProjectStatus.VALIDATING
    await update_project(project)

    spec_result = validate_project_spec(project.spec)
    diag_result = validate_diagram(project.diagram_json) if project.diagram_json else None
    fw_result = (
        validate_firmware_pins(project.firmware_code, project.spec)
        if project.firmware_code else None
    )

    # Merge results
    all_errors = list(spec_result.errors)
    all_warnings = list(spec_result.warnings)
    if diag_result:
        all_errors.extend(diag_result.errors)
        all_warnings.extend(diag_result.warnings)
    if fw_result:
        all_errors.extend(fw_result.errors)
        all_warnings.extend(fw_result.warnings)

    from schemas import ValidationResult
    combined = ValidationResult(
        valid=len(all_errors) == 0,
        errors=all_errors,
        warnings=all_warnings,
    )
    project.validation_result = combined
    project.status = ProjectStatus.VALIDATED if combined.valid else ProjectStatus.ERROR
    await update_project(project)

    return {
        "validation": combined.model_dump(),
        "project_status": project.status.value,
    }


# ── Compile ───────────────────────────────────────────────────────────────────

@app.post("/api/projects/{project_id}/compile")
async def compile_project(project_id: str):
    _validate_project_id(project_id)
    project = await get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    if not project.firmware_code:
        raise HTTPException(status_code=400, detail="No firmware to compile. Generate first.")
    if not arduino_cli_available():
        raise HTTPException(
            status_code=503,
            detail="arduino-cli not found. Install from https://arduino.github.io/arduino-cli/"
        )

    project.status = ProjectStatus.COMPILING
    await update_project(project)
    start = time.time()

    from pathlib import Path
    ws = Path(project.workspace_path)
    result = await compile_firmware(ws, project.name)

    duration_ms = int((time.time() - start) * 1000)
    log_text = f"STDOUT:\n{result['stdout']}\n\nSTDERR:\n{result['stderr']}"

    project.compilation_success = result["success"]
    project.compilation_log = log_text[:50000]  # cap size
    project.status = ProjectStatus.COMPILED if result["success"] else ProjectStatus.COMPILE_FAILED
    if result["success"]:
        project.simulation_status = SimulationStatus.READY

    await update_project(project)
    await log_operation(
        project_id, "compile",
        "success" if result["success"] else "error",
        duration_ms=duration_ms,
        exit_code=result["exit_code"],
        message=result["stderr"][:500] if not result["success"] else "Compiled successfully",
    )

    return {
        "success": result["success"],
        "exit_code": result["exit_code"],
        "stdout": result["stdout"][:10000],
        "stderr": result["stderr"][:10000],
        "binary_path": result.get("binary_path"),
        "project_status": project.status.value,
    }


# ── Repair ────────────────────────────────────────────────────────────────────

MAX_REPAIR_ATTEMPTS = 3


@app.post("/api/projects/{project_id}/repair")
async def repair_project(project_id: str):
    _validate_project_id(project_id)
    project = await get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    if not project.firmware_code:
        raise HTTPException(status_code=400, detail="No firmware to repair")
    if not project.compilation_log:
        raise HTTPException(status_code=400, detail="No compilation log. Compile first.")
    if len(project.repair_attempts) >= MAX_REPAIR_ATTEMPTS:
        raise HTTPException(
            status_code=400,
            detail=f"Maximum repair attempts ({MAX_REPAIR_ATTEMPTS}) reached."
        )

    attempt_num = len(project.repair_attempts) + 1
    project.status = ProjectStatus.REPAIRING
    await update_project(project)

    start = time.time()
    original_firmware = project.firmware_code

    try:
        repaired, raw = await repair_firmware(
            firmware=project.firmware_code,
            compiler_error=project.compilation_log,
            attempt_number=attempt_num,
        )

        # Validate patch: must have setup() and loop()
        if "void setup()" not in repaired or "void loop()" not in repaired:
            raise ValueError("Repaired firmware missing setup() or loop()")

        project.firmware_code = repaired
        await update_project(project)  # save before compile

        # Recompile
        from pathlib import Path
        ws = Path(project.workspace_path)
        compile_result = await compile_firmware(ws, project.name)

        log_text = f"STDOUT:\n{compile_result['stdout']}\n\nSTDERR:\n{compile_result['stderr']}"
        project.compilation_success = compile_result["success"]
        project.compilation_log = log_text[:50000]

        attempt = RepairAttempt(
            attempt_number=attempt_num,
            diagnosis=f"AI repair attempt {attempt_num}",
            patch_description="AI generated replacement firmware",
            files_affected=["sketch.ino"],
            rationale="Automated repair using Gemma3:1b",
            expected_verification="Arduino CLI compilation success",
            applied=True,
            compile_success=compile_result["success"],
            error_after=compile_result["stderr"][:500] if not compile_result["success"] else None,
            timestamp=datetime.utcnow().isoformat(),
        )
        project.repair_attempts.append(attempt)

        if compile_result["success"]:
            project.status = ProjectStatus.COMPILED
            project.simulation_status = SimulationStatus.READY
        else:
            project.status = ProjectStatus.COMPILE_FAILED
            if len(project.repair_attempts) >= MAX_REPAIR_ATTEMPTS:
                project.error_message = "Maximum repair attempts reached. Manual intervention required."

        await update_project(project)
        await log_operation(
            project_id, f"repair_attempt_{attempt_num}",
            "success" if compile_result["success"] else "error",
            duration_ms=int((time.time() - start) * 1000),
            exit_code=compile_result["exit_code"],
        )

        return {
            "attempt_number": attempt_num,
            "compile_success": compile_result["success"],
            "exit_code": compile_result["exit_code"],
            "stdout": compile_result["stdout"][:5000],
            "stderr": compile_result["stderr"][:5000],
            "attempts_remaining": MAX_REPAIR_ATTEMPTS - len(project.repair_attempts),
            "project_status": project.status.value,
        }

    except ValueError as e:
        # Restore original firmware
        project.firmware_code = original_firmware
        project.status = ProjectStatus.COMPILE_FAILED
        project.error_message = str(e)
        await update_project(project)
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        project.firmware_code = original_firmware
        project.status = ProjectStatus.COMPILE_FAILED
        await update_project(project)
        raise HTTPException(status_code=500, detail=str(e))


# ── Simulate ──────────────────────────────────────────────────────────────────

@app.get("/api/projects/{project_id}/wokwi-url")
async def get_wokwi_url(project_id: str):
    """
    Generate a Wokwi simulator URL for the project.
    Returns URL and instructions for opening the project in Wokwi.
    """
    _validate_project_id(project_id)
    project = await get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    if not project.diagram_json or not project.firmware_code:
        raise HTTPException(status_code=400, detail="Project needs both diagram and firmware to simulate")
    
    # Generate Wokwi project data
    wokwi_data = {
        "version": 1,
        "author": "CircuitForge AI",
        "editor": "wokwi",
        "parts": project.diagram_json.get("parts", []),
        "connections": project.diagram_json.get("connections", []),
    }
    
    return {
        "wokwi_url": "https://wokwi.com/",
        "project_data": wokwi_data,
        "firmware": project.firmware_code,
        "instructions": [
            "1. Open https://wokwi.com/",
            "2. Start a new ESP32 project",
            "3. Click on 'diagram.json' tab and paste the project_data",
            "4. Paste the firmware code into sketch.ino",
            "5. Click ▶ Play to simulate"
        ],
        "note": "Wokwi doesn't support direct URL embedding with custom circuits. Use the manual process above."
    }


@app.post("/api/projects/{project_id}/simulate")
async def simulate_project(project_id: str):
    _validate_project_id(project_id)
    project = await get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    import shutil
    wokwi_path = shutil.which("wokwi-cli")

    if wokwi_path is None:
        project.simulation_status = SimulationStatus.MANUAL
        await update_project(project)
        return {
            "simulation_status": SimulationStatus.MANUAL.value,
            "mode": "manual",
            "message": "wokwi-cli not installed. Use the Manual Wokwi workflow below.",
            "manual_steps": [
                "1. Open https://wokwi.com/",
                "2. Create a new ESP32 project",
                f"3. In your project workspace ({project.workspace_path}), find diagram.json and sketch.ino",
                "4. Replace diagram.json with the generated file",
                "5. Copy sketch.ino contents into the Wokwi editor",
                "6. Click the ▶ Play button to simulate",
            ],
            "wokwi_docs": "https://docs.wokwi.com/",
        }

    # wokwi-cli is available
    project.simulation_status = SimulationStatus.RUNNING
    await update_project(project)

    try:
        from pathlib import Path
        ws = Path(project.workspace_path)
        proc = await asyncio.create_subprocess_exec(
            wokwi_path, "run", "--timeout", "30", str(ws),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            out, err = await asyncio.wait_for(proc.communicate(), timeout=60)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            project.simulation_status = SimulationStatus.FAILED
            await update_project(project)
            return {"simulation_status": SimulationStatus.FAILED.value, "error": "Simulation timed out"}

        stdout = out.decode("utf-8", errors="replace")[:10000]
        stderr = err.decode("utf-8", errors="replace")[:10000]
        success = proc.returncode == 0

        project.simulation_status = SimulationStatus.PASSED if success else SimulationStatus.FAILED
        await update_project(project)

        return {
            "simulation_status": project.simulation_status.value,
            "exit_code": proc.returncode,
            "stdout": stdout,
            "stderr": stderr,
        }
    except Exception as e:
        project.simulation_status = SimulationStatus.UNAVAILABLE
        await update_project(project)
        return {"simulation_status": SimulationStatus.UNAVAILABLE.value, "error": str(e)}


# ── Security helpers ──────────────────────────────────────────────────────────

def _validate_project_id(project_id: str) -> None:
    """Reject malformed or path-traversal project IDs."""
    import re
    if not re.match(r'^[0-9a-f-]{36}$', project_id):
        raise HTTPException(status_code=400, detail="Invalid project ID format")


# ── Static Dashboard Mount ───────────────────────────────────────────────────

from fastapi.staticfiles import StaticFiles

static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")


# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        reload_dirs=[os.path.dirname(os.path.abspath(__file__))],
    )
