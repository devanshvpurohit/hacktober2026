"""
CircuitForge AI - Project and Wiring Validators
Runs deterministic checks on project specs, pin assignments, wiring, and diagrams.
"""
from __future__ import annotations
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from schemas import (
    ProjectSpec, ValidationResult, ValidationError as VError,
    PinAssignment, Connection, ComponentInstance
)
from catalog.components import (
    CATALOG, ESP32_VALID_GPIO, ESP32_OUTPUT_GPIO, ESP32_ANALOG_GPIO, get_component
)


def _err(code: str, msg: str, field: str | None = None) -> VError:
    return VError(code=code, severity="error", message=msg, field=field)


def _warn(code: str, msg: str, field: str | None = None) -> VError:
    return VError(code=code, severity="warning", message=msg, field=field)


def validate_project_spec(spec: ProjectSpec) -> ValidationResult:
    """Run all validators against a project specification."""
    errors: list[VError] = []
    warnings: list[VError] = []

    # 1. Validate components exist in catalog
    for inst in spec.components:
        if inst.catalog_id not in CATALOG:
            errors.append(_err(
                "UNKNOWN_COMPONENT",
                f"Component '{inst.catalog_id}' (instance '{inst.instance_id}') not found in catalog.",
                field="components"
            ))
        else:
            cat = CATALOG[inst.catalog_id]
            if spec.board.value not in cat.supported_boards:
                errors.append(_err(
                    "UNSUPPORTED_BOARD",
                    f"Component '{inst.catalog_id}' does not support board '{spec.board.value}'.",
                    field="components"
                ))

    # 2. Validate GPIO pin assignments
    used_gpio: dict[int, str] = {}  # gpio -> instance_id
    for pa in spec.pin_assignments:
        gpio = pa.gpio_pin

        if spec.board == "esp32" or spec.board.value == "esp32":
            if gpio not in ESP32_VALID_GPIO:
                errors.append(_err(
                    "INVALID_GPIO",
                    f"GPIO{gpio} is not a valid/usable GPIO on ESP32 (reserved or does not exist).",
                    field="pin_assignments"
                ))

        # Check for conflicts
        if gpio in used_gpio:
            errors.append(_err(
                "GPIO_CONFLICT",
                f"GPIO{gpio} is assigned to both '{used_gpio[gpio]}' and '{pa.component_instance}'.",
                field="pin_assignments"
            ))
        else:
            used_gpio[gpio] = pa.component_instance

    # 3. Validate connections reference existing component instances
    instance_ids = {inst.instance_id for inst in spec.components}
    instance_ids.add("board")  # board is always a valid target

    for conn in spec.connections:
        if conn.from_component not in instance_ids and conn.from_component != "board":
            errors.append(_err(
                "UNKNOWN_CONNECTION_COMPONENT",
                f"Connection references unknown component '{conn.from_component}'.",
                field="connections"
            ))
        if conn.to_component not in instance_ids and conn.to_component != "board":
            errors.append(_err(
                "UNKNOWN_CONNECTION_COMPONENT",
                f"Connection references unknown component '{conn.to_component}'.",
                field="connections"
            ))

    # 4. Check required libraries are listed
    for inst in spec.components:
        if inst.catalog_id in CATALOG:
            cat = CATALOG[inst.catalog_id]
            for lib in cat.libraries:
                if lib not in spec.libraries:
                    warnings.append(_warn(
                        "MISSING_LIBRARY",
                        f"Library '{lib}' required by '{inst.catalog_id}' is not in libraries list.",
                        field="libraries"
                    ))

    # 5. Firmware consistency: if firmware is provided, check pin references
    # (Done separately in validate_firmware_pins)

    # 6. Check for duplicate instance IDs
    seen_ids: set[str] = set()
    for inst in spec.components:
        if inst.instance_id in seen_ids:
            errors.append(_err(
                "DUPLICATE_INSTANCE_ID",
                f"Duplicate component instance ID: '{inst.instance_id}'.",
                field="components"
            ))
        seen_ids.add(inst.instance_id)

    return ValidationResult(
        valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
    )


def validate_diagram(diagram: dict) -> ValidationResult:
    """Validate Wokwi-compatible diagram.json structure."""
    errors: list[VError] = []
    warnings: list[VError] = []

    if not isinstance(diagram, dict):
        return ValidationResult(valid=False, errors=[
            _err("INVALID_DIAGRAM", "Diagram must be a JSON object.")
        ])

    # Required top-level keys
    for key in ["version", "author", "editor", "parts", "connections"]:
        if key not in diagram:
            errors.append(_err("MISSING_DIAGRAM_KEY", f"Diagram missing required key: '{key}'.", field=key))

    if "parts" in diagram:
        parts = diagram["parts"]
        if not isinstance(parts, list):
            errors.append(_err("INVALID_PARTS", "Diagram 'parts' must be a list."))
        else:
            part_ids: set[str] = set()
            for i, part in enumerate(parts):
                if not isinstance(part, dict):
                    errors.append(_err("INVALID_PART", f"Part[{i}] must be a JSON object."))
                    continue
                for field in ["id", "type"]:
                    if field not in part:
                        errors.append(_err("MISSING_PART_FIELD", f"Part[{i}] missing field '{field}'.", field=f"parts[{i}]"))
                if "id" in part:
                    if part["id"] in part_ids:
                        errors.append(_err("DUPLICATE_PART_ID", f"Duplicate part ID: '{part['id']}'."))
                    part_ids.add(part["id"])

    if "connections" in diagram:
        conns = diagram["connections"]
        if not isinstance(conns, list):
            errors.append(_err("INVALID_CONNECTIONS", "Diagram 'connections' must be a list."))
        else:
            for i, conn in enumerate(conns):
                if not isinstance(conn, list) or len(conn) < 2:
                    errors.append(_err("INVALID_CONNECTION", f"Connection[{i}] must be a list with at least 2 elements."))

    return ValidationResult(valid=len(errors) == 0, errors=errors, warnings=warnings)


def validate_firmware_pins(firmware: str, spec: ProjectSpec) -> ValidationResult:
    """Check that firmware #define pin constants match the spec's pin assignments."""
    errors: list[VError] = []
    warnings: list[VError] = []

    for pa in spec.pin_assignments:
        # Look for common patterns like: #define DHTPIN 4
        pin_num = str(pa.gpio_pin)
        pin_name_upper = pa.component_pin.upper().replace("-", "_")

        # Simple heuristic: check if the GPIO number appears in firmware
        if pin_num not in firmware:
            warnings.append(_warn(
                "PIN_NOT_IN_FIRMWARE",
                f"GPIO{pa.gpio_pin} for '{pa.component_instance}.{pa.component_pin}' "
                f"not found in firmware. Verify pin assignment matches firmware defines.",
                field="firmware"
            ))

    return ValidationResult(valid=len(errors) == 0, errors=errors, warnings=warnings)


def validate_zip_contents(zip_path: str, required_files: list[str]) -> ValidationResult:
    """Check that a generated ZIP contains required files."""
    import zipfile
    errors: list[VError] = []
    warnings: list[VError] = []

    try:
        with zipfile.ZipFile(zip_path, 'r') as zf:
            names = zf.namelist()
            # Normalize to basenames for comparison
            basenames = {os.path.basename(n) for n in names}
            for f in required_files:
                base = os.path.basename(f)
                if base not in basenames and f not in names:
                    errors.append(_err("MISSING_ZIP_FILE", f"Required file '{f}' not found in ZIP archive."))
    except zipfile.BadZipFile:
        errors.append(_err("INVALID_ZIP", "Generated file is not a valid ZIP archive."))
    except Exception as e:
        errors.append(_err("ZIP_ERROR", f"Error reading ZIP: {e}"))

    return ValidationResult(valid=len(errors) == 0, errors=errors, warnings=warnings)
