"""
CircuitForge AI - SQLite Storage Layer
Handles project persistence using SQLite metadata + local filesystem artifacts.
"""
from __future__ import annotations
import json
import os
import sys
import uuid
import shutil
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Optional

import aiosqlite

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from schemas import Project, ProjectSummary, ProjectStatus, SimulationStatus

# ── Paths ─────────────────────────────────────────────────────────────────────

BACKEND_DIR = Path(__file__).parent.parent
WORKSPACE_DIR = BACKEND_DIR.parent.parent / "workspace" / "projects"
DB_PATH = BACKEND_DIR.parent.parent / "workspace" / "circuitforge.db"


def _workspace_path(project_id: str) -> Path:
    return WORKSPACE_DIR / project_id


def _ensure_workspace(project_id: str) -> Path:
    p = _workspace_path(project_id)
    p.mkdir(parents=True, exist_ok=True)
    return p


# ── Database Setup ─────────────────────────────────────────────────────────────

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS projects (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT NOT NULL,
    user_request TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'created',
    simulation_status TEXT NOT NULL DEFAULT 'not_simulated',
    spec_json TEXT,
    firmware_code TEXT,
    diagram_json TEXT,
    validation_json TEXT,
    compilation_success INTEGER,
    compilation_log TEXT,
    repair_attempts_json TEXT,
    bom_json TEXT,
    error_message TEXT,
    workspace_path TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""

CREATE_LOGS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS operation_logs (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    operation TEXT NOT NULL,
    status TEXT NOT NULL,
    duration_ms INTEGER,
    exit_code INTEGER,
    message TEXT,
    created_at TEXT NOT NULL
);
"""


async def init_db() -> None:
    """Initialize SQLite database and create tables if they don't exist."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(str(DB_PATH)) as db:
        await db.execute(CREATE_TABLE_SQL)
        await db.execute(CREATE_LOGS_TABLE_SQL)
        await db.commit()


# ── Project CRUD ───────────────────────────────────────────────────────────────

async def create_project(user_request: str) -> Project:
    project = Project(
        id=str(uuid.uuid4()),
        name="New Project",
        description="Generating from your request...",
        user_request=user_request,
        status=ProjectStatus.CREATED,
        simulation_status=SimulationStatus.NOT_SIMULATED,
        created_at=datetime.utcnow().isoformat(),
        updated_at=datetime.utcnow().isoformat(),
    )
    ws_path = _ensure_workspace(project.id)
    project.workspace_path = str(ws_path)

    async with aiosqlite.connect(str(DB_PATH)) as db:
        await db.execute(
            """INSERT INTO projects
               (id, name, description, user_request, status, simulation_status,
                workspace_path, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (project.id, project.name, project.description, project.user_request,
             project.status.value, project.simulation_status.value,
             str(ws_path), project.created_at, project.updated_at)
        )
        await db.commit()

    return project


async def get_project(project_id: str) -> Optional[Project]:
    async with aiosqlite.connect(str(DB_PATH)) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM projects WHERE id = ?", (project_id,)) as cursor:
            row = await cursor.fetchone()
            if row is None:
                return None
            return _row_to_project(dict(row))


async def update_project(project: Project) -> None:
    project.updated_at = datetime.utcnow().isoformat()
    ws_path = _ensure_workspace(project.id)
    project.workspace_path = str(ws_path)

    async with aiosqlite.connect(str(DB_PATH)) as db:
        await db.execute(
            """UPDATE projects SET
               name=?, description=?, status=?, simulation_status=?,
               spec_json=?, firmware_code=?, diagram_json=?,
               validation_json=?, compilation_success=?, compilation_log=?,
               repair_attempts_json=?, bom_json=?, error_message=?,
               workspace_path=?, updated_at=?
               WHERE id=?""",
            (
                project.name,
                project.description,
                project.status.value,
                project.simulation_status.value,
                project.spec.model_dump_json() if project.spec else None,
                project.firmware_code,
                json.dumps(project.diagram_json) if project.diagram_json else None,
                project.validation_result.model_dump_json() if project.validation_result else None,
                1 if project.compilation_success else (0 if project.compilation_success is False else None),
                project.compilation_log,
                json.dumps([r.model_dump() for r in project.repair_attempts]) if project.repair_attempts else None,
                project.bom.model_dump_json() if project.bom else None,
                project.error_message,
                project.workspace_path,
                project.updated_at,
                project.id,
            )
        )
        await db.commit()

    # Write artifact files to workspace
    await _write_artifacts(project)


async def _write_artifacts(project: Project) -> None:
    """Write project artifacts to workspace directory atomically."""
    ws = Path(project.workspace_path)
    ws.mkdir(parents=True, exist_ok=True)

    # project.json
    proj_file = ws / "project.json"
    tmp = proj_file.with_suffix(".tmp")
    tmp.write_text(project.model_dump_json(indent=2), encoding="utf-8")
    tmp.replace(proj_file)

    # diagram.json
    if project.diagram_json:
        diag_file = ws / "diagram.json"
        tmp = diag_file.with_suffix(".tmp")
        tmp.write_text(json.dumps(project.diagram_json, indent=2), encoding="utf-8")
        tmp.replace(diag_file)

    # sketch.ino
    if project.firmware_code:
        sketch_file = ws / "sketch.ino"
        tmp = sketch_file.with_suffix(".tmp")
        tmp.write_text(project.firmware_code, encoding="utf-8")
        tmp.replace(sketch_file)

    # libraries.txt
    if project.spec and project.spec.libraries:
        lib_file = ws / "libraries.txt"
        lib_file.write_text("\n".join(project.spec.libraries), encoding="utf-8")

    # wokwi.toml
    if project.spec:
        board = project.spec.board.value
        toml_content = f"""[wokwi]
version = 1
firmware = "build/{project.name.replace(' ', '_')}.ino.bin"
elf = "build/{project.name.replace(' ', '_')}.ino.elf"

[esp32]
# ESP32 board configuration
"""
        (ws / "wokwi.toml").write_text(toml_content, encoding="utf-8")

    # README
    _write_readme(project, ws)


def _write_readme(project: Project, ws: Path) -> None:
    lines = [
        f"# {project.name}",
        "",
        f"> {project.description}",
        "",
        "## User Request",
        "",
        project.user_request,
        "",
        "## Status",
        "",
        f"- Project Status: `{project.status.value}`",
        f"- Simulation Status: `{project.simulation_status.value}`",
        f"- Compilation: `{'Success' if project.compilation_success else 'Not compiled' if project.compilation_success is None else 'Failed'}`",
        "",
    ]
    if project.spec:
        lines += [
            "## Components",
            "",
        ]
        for inst in project.spec.components:
            lines.append(f"- **{inst.name}** (`{inst.catalog_id}`)")
        lines.append("")
        if project.spec.libraries:
            lines += ["## Required Libraries", ""]
            for lib in project.spec.libraries:
                lines.append(f"- {lib}")
            lines.append("")

    lines += [
        "## Wokwi Simulation (Manual)",
        "",
        "1. Open [Wokwi](https://wokwi.com/)",
        "2. Create a new ESP32 project",
        "3. Replace `diagram.json` with the generated `diagram.json`",
        "4. Copy `sketch.ino` contents into the editor",
        "5. Click Run to simulate",
        "",
        "---",
        "*Generated by CircuitForge AI*",
    ]
    (ws / "README.md").write_text("\n".join(lines), encoding="utf-8")


async def list_projects() -> list[ProjectSummary]:
    async with aiosqlite.connect(str(DB_PATH)) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT id, name, description, status, simulation_status, "
            "compilation_success, created_at, updated_at FROM projects ORDER BY created_at DESC"
        ) as cursor:
            rows = await cursor.fetchall()
            return [
                ProjectSummary(
                    id=row["id"],
                    name=row["name"],
                    description=row["description"],
                    status=ProjectStatus(row["status"]),
                    simulation_status=SimulationStatus(row["simulation_status"]),
                    compilation_success=bool(row["compilation_success"]) if row["compilation_success"] is not None else None,
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                )
                for row in rows
            ]


async def delete_project(project_id: str) -> bool:
    project = await get_project(project_id)
    if project is None:
        return False

    # Remove workspace
    ws = _workspace_path(project_id)
    if ws.exists():
        shutil.rmtree(ws, ignore_errors=True)

    async with aiosqlite.connect(str(DB_PATH)) as db:
        await db.execute("DELETE FROM projects WHERE id = ?", (project_id,))
        await db.execute("DELETE FROM operation_logs WHERE project_id = ?", (project_id,))
        await db.commit()
    return True


async def get_project_logs(project_id: str) -> list[dict]:
    async with aiosqlite.connect(str(DB_PATH)) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM operation_logs WHERE project_id = ? ORDER BY created_at DESC LIMIT 100",
            (project_id,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]


async def log_operation(
    project_id: str, operation: str, status: str,
    duration_ms: Optional[int] = None, exit_code: Optional[int] = None,
    message: Optional[str] = None
) -> None:
    async with aiosqlite.connect(str(DB_PATH)) as db:
        await db.execute(
            """INSERT INTO operation_logs (id, project_id, operation, status, duration_ms, exit_code, message, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (str(uuid.uuid4()), project_id, operation, status,
             duration_ms, exit_code, message, datetime.utcnow().isoformat())
        )
        await db.commit()


# ── ZIP Export ────────────────────────────────────────────────────────────────

async def export_project_zip(project_id: str) -> Optional[str]:
    """
    Create a ZIP of all project artifacts.
    Returns the path to the ZIP file, or None if project not found.
    Excludes: credentials, tokens, .env, internal DB, unrelated app files.
    """
    project = await get_project(project_id)
    if project is None:
        return None

    ws = _workspace_path(project_id)
    if not ws.exists():
        return None

    zip_path = ws / f"{project_id}_export.zip"
    allowed_extensions = {".ino", ".json", ".txt", ".md", ".toml", ".cpp", ".h", ".bin", ".elf"}
    excluded_names = {".env", ".env.local", "circuitforge.db", ".DS_Store"}

    with zipfile.ZipFile(str(zip_path), "w", zipfile.ZIP_DEFLATED) as zf:
        for file_path in ws.rglob("*"):
            if not file_path.is_file():
                continue
            if file_path.name in excluded_names:
                continue
            if file_path.suffix not in allowed_extensions and file_path.name not in allowed_extensions:
                continue
            if file_path.name.endswith("_export.zip"):
                continue
            # Path traversal guard
            try:
                file_path.relative_to(ws)
            except ValueError:
                continue
            arc_name = file_path.relative_to(ws)
            zf.write(str(file_path), str(arc_name))

    return str(zip_path)


# ── Row → Project ─────────────────────────────────────────────────────────────

def _row_to_project(row: dict) -> Project:
    from schemas import ProjectSpec, ValidationResult, BOM, RepairAttempt

    spec = None
    if row.get("spec_json"):
        try:
            spec = ProjectSpec.model_validate_json(row["spec_json"])
        except Exception:
            spec = None

    diagram = None
    if row.get("diagram_json"):
        try:
            diagram = json.loads(row["diagram_json"])
        except Exception:
            diagram = None

    validation = None
    if row.get("validation_json"):
        try:
            validation = ValidationResult.model_validate_json(row["validation_json"])
        except Exception:
            validation = None

    bom = None
    if row.get("bom_json"):
        try:
            bom = BOM.model_validate_json(row["bom_json"])
        except Exception:
            bom = None

    repair_attempts = []
    if row.get("repair_attempts_json"):
        try:
            raw = json.loads(row["repair_attempts_json"])
            repair_attempts = [RepairAttempt(**r) for r in raw]
        except Exception:
            repair_attempts = []

    compilation_success = None
    if row.get("compilation_success") is not None:
        compilation_success = bool(row["compilation_success"])

    return Project(
        id=row["id"],
        name=row["name"],
        description=row["description"],
        user_request=row["user_request"],
        status=ProjectStatus(row["status"]),
        simulation_status=SimulationStatus(row["simulation_status"]),
        spec=spec,
        firmware_code=row.get("firmware_code"),
        diagram_json=diagram,
        validation_result=validation,
        compilation_success=compilation_success,
        compilation_log=row.get("compilation_log"),
        repair_attempts=repair_attempts,
        bom=bom,
        error_message=row.get("error_message"),
        workspace_path=row.get("workspace_path"),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )
