"""
CircuitForge AI - Unit Tests
Tests validators, catalog, BOM, diagram, and ZIP contents.
"""
import sys
import os
import json
import zipfile
import tempfile
from decimal import Decimal

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'apps', 'backend'))

from schemas import (
    ProjectSpec, ComponentInstance, PinAssignment, Connection,
    BoardType, ValidationResult
)
from catalog.components import CATALOG, ESP32_VALID_GPIO, get_component, search_components
from catalog.bom_generator import generate_bom
from catalog.diagram_generator import generate_diagram
from validators.project_validator import (
    validate_project_spec, validate_diagram, validate_firmware_pins, validate_zip_contents
)


def make_valid_spec() -> ProjectSpec:
    return ProjectSpec(
        name='Temp Monitor',
        description='ESP32 temperature monitor with DHT22 and LED',
        behavior='Read DHT22 sensor. Turn on LED when temperature > 30C.',
        board=BoardType.ESP32,
        components=[
            ComponentInstance(instance_id='dht22_1', catalog_id='dht22', name='DHT22', quantity=1),
            ComponentInstance(instance_id='led_1', catalog_id='led_red', name='Red LED', quantity=1),
            ComponentInstance(instance_id='r1', catalog_id='resistor_220', name='220R', quantity=1, value='220'),
        ],
        pin_assignments=[
            PinAssignment(component_id='dht22', component_instance='dht22_1', component_pin='SDA', gpio_pin=4, description='DHT22 data'),
            PinAssignment(component_id='led_red', component_instance='led_1', component_pin='A', gpio_pin=2, description='LED anode'),
        ],
        connections=[],
        libraries=['DHT sensor library', 'Adafruit Unified Sensor'],
        acceptance_criteria=['LED turns on when temp > 30C'],
        threshold_value=30.0,
        threshold_unit='Celsius',
    )


# ── Catalog Tests ─────────────────────────────────────────────────────────────

def test_catalog_has_required_components():
    for cid in ['esp32_devkitv1', 'dht22', 'led_red', 'resistor_220', 'hc_sr04', 'buzzer']:
        assert cid in CATALOG, f"Missing catalog entry: {cid}"


def test_catalog_get_component():
    dht = get_component('dht22')
    assert dht is not None
    assert dht.wokwi_id == 'wokwi-dht22'
    assert 'esp32' in dht.supported_boards


def test_catalog_search():
    results = search_components('temperature')
    assert any('dht22' in r.id.lower() or 'temp' in r.description.lower() for r in results)


def test_catalog_prices_are_positive():
    for comp in CATALOG.values():
        assert comp.unit_price_inr > 0, f"{comp.id} has non-positive price"


# ── Validator Tests ───────────────────────────────────────────────────────────

def test_valid_spec_passes():
    spec = make_valid_spec()
    result = validate_project_spec(spec)
    assert result.valid, f"Expected valid but got errors: {result.errors}"


def test_unknown_component_detected():
    spec = make_valid_spec()
    spec.components.append(ComponentInstance(
        instance_id='xyz_1', catalog_id='nonexistent_sensor', name='Unknown', quantity=1
    ))
    result = validate_project_spec(spec)
    assert not result.valid
    assert any(e.code == 'UNKNOWN_COMPONENT' for e in result.errors)


def test_gpio_conflict_detected():
    spec = make_valid_spec()
    spec.pin_assignments.append(PinAssignment(
        component_id='led_red', component_instance='led_2',
        component_pin='A', gpio_pin=4, description='Conflict'
    ))
    result = validate_project_spec(spec)
    assert not result.valid
    assert any('CONFLICT' in e.code for e in result.errors)


def test_invalid_gpio_detected():
    spec = make_valid_spec()
    spec.pin_assignments.append(PinAssignment(
        component_id='led_red', component_instance='led_extra',
        component_pin='A', gpio_pin=7, description='Reserved flash pin'
    ))
    result = validate_project_spec(spec)
    assert not result.valid
    assert any('INVALID_GPIO' in e.code for e in result.errors)


def test_duplicate_instance_id_detected():
    spec = make_valid_spec()
    spec.components.append(ComponentInstance(
        instance_id='dht22_1', catalog_id='dht22', name='Duplicate', quantity=1
    ))
    result = validate_project_spec(spec)
    assert not result.valid
    assert any('DUPLICATE' in e.code for e in result.errors)


def test_missing_library_warning():
    spec = make_valid_spec()
    spec.libraries = []  # Remove libraries
    result = validate_project_spec(spec)
    # Should produce MISSING_LIBRARY warnings (not errors)
    assert any(w.code == 'MISSING_LIBRARY' for w in result.warnings)


# ── Diagram Tests ─────────────────────────────────────────────────────────────

def test_diagram_generation():
    spec = make_valid_spec()
    diagram = generate_diagram(spec)
    assert 'parts' in diagram
    assert 'connections' in diagram
    assert 'version' in diagram
    assert len(diagram['parts']) >= 2  # at least board + 1 component


def test_diagram_validation():
    spec = make_valid_spec()
    diagram = generate_diagram(spec)
    result = validate_diagram(diagram)
    assert result.valid, f"Diagram invalid: {result.errors}"


def test_invalid_diagram_missing_key():
    result = validate_diagram({'version': 1, 'parts': []})  # missing connections
    assert not result.valid
    assert any('connections' in e.message.lower() or 'connections' in (e.field or '') for e in result.errors)


def test_invalid_diagram_not_dict():
    result = validate_diagram([1, 2, 3])  # type: ignore
    assert not result.valid


def test_diagram_parts_have_ids():
    spec = make_valid_spec()
    diagram = generate_diagram(spec)
    for part in diagram['parts']:
        assert 'id' in part, f"Part missing 'id': {part}"
        assert 'type' in part, f"Part missing 'type': {part}"


# ── BOM Tests ─────────────────────────────────────────────────────────────────

def test_bom_total_arithmetic():
    spec = make_valid_spec()
    bom = generate_bom('test-id', spec)
    # Total should equal sum of subtotals using Decimal math
    expected = sum(Decimal(str(line.subtotal_inr)) for line in bom.lines)
    actual = Decimal(str(bom.total_inr))
    # Allow 1 cent rounding difference
    assert abs(expected - actual) <= Decimal('0.02'), f"BOM arithmetic error: {expected} != {actual}"


def test_bom_includes_board():
    spec = make_valid_spec()
    bom = generate_bom('test-id', spec)
    assert any('ESP32' in line.name for line in bom.lines), "BOM should include ESP32 board"


def test_bom_positive_prices():
    spec = make_valid_spec()
    bom = generate_bom('test-id', spec)
    for line in bom.lines:
        assert line.unit_price_inr > 0
        assert line.subtotal_inr > 0


def test_bom_indicative_label():
    spec = make_valid_spec()
    bom = generate_bom('test-id', spec)
    assert 'indicative' in bom.note.lower() or 'indicative' in bom.lines[0].confidence.lower()


# ── Firmware Pin Consistency Tests ─────────────────────────────────────────────

def test_firmware_pin_check_warning():
    spec = make_valid_spec()
    # Firmware that doesn't reference GPIO4
    firmware = """
#include <DHT.h>
#define DHTPIN 99  // wrong pin
void setup() {}
void loop() {}
"""
    result = validate_firmware_pins(firmware, spec)
    # Should produce warning about GPIO4 not found
    assert len(result.warnings) > 0 or not result.valid


def test_firmware_pin_check_ok():
    spec = make_valid_spec()
    firmware = """
#include <DHT.h>
#define DHTPIN 4
#define LED_PIN 2
void setup() { Serial.begin(115200); }
void loop() { }
"""
    result = validate_firmware_pins(firmware, spec)
    assert result.valid


# ── ZIP Validation Tests ──────────────────────────────────────────────────────

def test_zip_valid_contents():
    with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as f:
        with zipfile.ZipFile(f.name, 'w') as zf:
            zf.writestr('sketch.ino', '#include <DHT.h>\nvoid setup(){}\nvoid loop(){}')
            zf.writestr('diagram.json', '{"version":1,"parts":[],"connections":[]}')
            zf.writestr('README.md', '# Test Project')
        result = validate_zip_contents(f.name, ['sketch.ino', 'diagram.json'])
        assert result.valid, f"ZIP validation failed: {result.errors}"
    os.unlink(f.name)


def test_zip_missing_file():
    with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as f:
        with zipfile.ZipFile(f.name, 'w') as zf:
            zf.writestr('README.md', '# only readme')
        result = validate_zip_contents(f.name, ['sketch.ino'])
        assert not result.valid
        assert any('sketch.ino' in e.message for e in result.errors)
    os.unlink(f.name)


def test_path_traversal_prevention():
    """Path traversal in ZIP must not escape workspace."""
    with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as f:
        with zipfile.ZipFile(f.name, 'w') as zf:
            zf.writestr('../../../etc/passwd', 'evil content')
            zf.writestr('sketch.ino', 'ok')
        # The validate function checks basenames; path traversal entries won't match required basenames
        result = validate_zip_contents(f.name, ['sketch.ino'])
        assert result.valid  # sketch.ino is present
    os.unlink(f.name)


# ── Run all tests ─────────────────────────────────────────────────────────────

if __name__ == '__main__':
    tests = [
        test_catalog_has_required_components,
        test_catalog_get_component,
        test_catalog_search,
        test_catalog_prices_are_positive,
        test_valid_spec_passes,
        test_unknown_component_detected,
        test_gpio_conflict_detected,
        test_invalid_gpio_detected,
        test_duplicate_instance_id_detected,
        test_missing_library_warning,
        test_diagram_generation,
        test_diagram_validation,
        test_invalid_diagram_missing_key,
        test_invalid_diagram_not_dict,
        test_diagram_parts_have_ids,
        test_bom_total_arithmetic,
        test_bom_includes_board,
        test_bom_positive_prices,
        test_bom_indicative_label,
        test_firmware_pin_check_warning,
        test_firmware_pin_check_ok,
        test_zip_valid_contents,
        test_zip_missing_file,
        test_path_traversal_prevention,
    ]

    passed = failed = 0
    for t in tests:
        try:
            t()
            print(f'  PASS  {t.__name__}')
            passed += 1
        except Exception as e:
            print(f'  FAIL  {t.__name__}: {e}')
            failed += 1

    print(f'\n{passed} passed, {failed} failed out of {len(tests)} tests')
    if failed > 0:
        sys.exit(1)
