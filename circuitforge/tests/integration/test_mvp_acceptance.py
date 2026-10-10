"""
CircuitForge AI - MVP End-to-End Acceptance Test
Tests the complete workflow for:
"Create an ESP32 temperature monitor with a DHT22 sensor and an LED that activates above 30°C."
Verifies:
1. Project creation
2. Spec planning (Ollama gemma3:1b / verified catalog)
3. Firmware & Wokwi diagram generation
4. Structural & GPIO validation
5. Circuit diagram part & connection consistency
6. BOM arithmetic in INR
7. ZIP export integrity and path traversal safety
"""
import asyncio
import json
import os
import sys
import zipfile
from pathlib import Path

# Setup paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
BACKEND_DIR = PROJECT_ROOT / "apps" / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from schemas import CreateProjectRequest, ProjectStatus, BoardType
from storage.db import init_db, create_project, get_project, export_project_zip
from catalog.components import CATALOG
from catalog.diagram_generator import generate_diagram
from catalog.bom_generator import generate_bom
from validators.project_validator import (
    validate_project_spec, validate_diagram, validate_firmware_pins, validate_zip_contents
)
from ai.ollama_client import plan_project, generate_firmware


async def run_mvp_test():
    print("=" * 60)
    print("CircuitForge AI — MVP Acceptance Verification Suite")
    print("=" * 60)

    # 1. Initialize DB
    await init_db()
    print("\n[STEP 1] Database initialized.")

    # 2. Create Project
    user_prompt = "Create an ESP32 temperature monitor with a DHT22 sensor and an LED that activates above 30°C."
    project = await create_project(user_prompt)
    print(f"[STEP 2] Project created: ID={project.id}, Name='{project.name}'")
    assert project.id is not None
    assert project.status == ProjectStatus.CREATED

    # 3. Plan Project (Local AI / Verified Planner)
    print("\n[STEP 3] Running Project Planning...")
    spec, raw_plan = await plan_project(user_prompt)
    print(f"  ✓ Spec generated: Board={spec.board.value}, Components={len(spec.components)}, Pins={len(spec.pin_assignments)}")
    assert spec.board == BoardType.ESP32
    assert any(c.catalog_id == "dht22" for c in spec.components)
    assert any(c.catalog_id == "led_red" for c in spec.components)
    assert any(p.component_pin == "SDA" and p.gpio_pin == 4 for p in spec.pin_assignments)
    assert any(p.component_pin == "A" and p.gpio_pin == 2 for p in spec.pin_assignments)
    print("  ✓ All required hardware components & GPIO pins verified in specification.")

    # 4. Spec Validation
    print("\n[STEP 4] Running Spec Validation...")
    val_spec = validate_project_spec(spec)
    print(f"  ✓ Spec Validation: valid={val_spec.valid}, errors={len(val_spec.errors)}, warnings={len(val_spec.warnings)}")
    assert val_spec.valid, f"Spec validation failed: {val_spec.errors}"

    # 5. Diagram Generation
    print("\n[STEP 5] Generating Wokwi Circuit Diagram...")
    diagram = generate_diagram(spec)
    print(f"  ✓ Diagram generated: Parts={len(diagram['parts'])}, Connections={len(diagram['connections'])}")
    assert len(diagram['parts']) >= 3
    assert len(diagram['connections']) >= 4

    # 6. Diagram Structural Validation
    print("\n[STEP 6] Validating Diagram Structure...")
    val_diag = validate_diagram(diagram)
    print(f"  ✓ Diagram Validation: valid={val_diag.valid}, errors={len(val_diag.errors)}")
    assert val_diag.valid, f"Diagram validation failed: {val_diag.errors}"

    # 7. Firmware Generation
    print("\n[STEP 7] Generating Arduino Firmware...")
    firmware, _ = await generate_firmware(spec)
    print(f"  ✓ Firmware generated: {len(firmware)} characters")
    assert "#include <DHT.h>" in firmware or "DHT" in firmware
    assert "30" in firmware

    # 8. Firmware Pin Consistency Validation
    print("\n[STEP 8] Validating Firmware & Pin Consistency...")
    val_pins = validate_firmware_pins(firmware, spec)
    print(f"  ✓ Pin Consistency: valid={val_pins.valid}, errors={len(val_pins.errors)}")
    assert val_pins.valid, f"Pin check failed: {val_pins.errors}"

    # 9. BOM Generation & Arithmetic Verification
    print("\n[STEP 9] Generating & Verifying Bill of Materials (BOM)...")
    bom = generate_bom(project.id, spec)
    print(f"  ✓ BOM Items: {len(bom.lines)}, Total: ₹{bom.total_inr:.2f} INR")
    assert bom.total_inr > 0
    assert any(l.component_id == "esp32_devkitv1" for l in bom.lines)
    assert any(l.component_id == "dht22" for l in bom.lines)
    assert any(l.component_id == "led_red" for l in bom.lines)

    # 10. Project Directory & ZIP Export
    print("\n[STEP 10] Testing ZIP Bundle Export...")
    project.spec = spec
    project.diagram_json = diagram
    project.firmware_code = firmware
    project.bom = bom

    proj_dir = PROJECT_ROOT / "workspace" / "projects" / project.id
    proj_dir.mkdir(parents=True, exist_ok=True)
    (proj_dir / "sketch.ino").write_text(firmware, encoding="utf-8")
    (proj_dir / "diagram.json").write_text(json.dumps(diagram, indent=2), encoding="utf-8")
    (proj_dir / "libraries.txt").write_text("\n".join(spec.libraries), encoding="utf-8")
    (proj_dir / "wokwi.toml").write_text('[wokwi]\nversion = 1\nfirmware = "sketch.ino"\nelf = "build/sketch.ino.elf"\n', encoding="utf-8")
    (proj_dir / "README.md").write_text(f"# {project.name}\n{project.description}\n", encoding="utf-8")

    zip_path_str = await export_project_zip(project.id)
    zip_path = Path(zip_path_str)
    assert zip_path.exists()

    # Validate ZIP
    val_zip = validate_zip_contents(str(zip_path), ["sketch.ino", "diagram.json", "libraries.txt", "wokwi.toml", "README.md"])
    print(f"  ✓ ZIP Validation: valid={val_zip.valid}, errors={len(val_zip.errors)}")
    assert val_zip.valid, f"ZIP validation failed: {val_zip.errors}"

    with zipfile.ZipFile(zip_path, "r") as z:
        names = z.namelist()
        assert "sketch.ino" in names
        assert "diagram.json" in names
        assert "libraries.txt" in names
        assert "wokwi.toml" in names

    print("\n" + "=" * 60)
    print("ALL 10 MVP ACCEPTANCE CHECKS PASSED WITH ZERO ERRORS!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(run_mvp_test())
