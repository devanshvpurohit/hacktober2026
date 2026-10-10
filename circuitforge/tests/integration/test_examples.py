"""
CircuitForge AI - Integration Tests for Built-in Examples
Validates that all 3 example projects:
1. Have valid Wokwi-compatible diagram.json
2. Contain valid sketch.ino and correct pin configurations
3. Contain valid libraries.txt and wokwi.toml
4. Match component catalog constraints
"""
import os
import sys
import json
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'apps', 'backend'))

from catalog.components import CATALOG, ESP32_VALID_GPIO
from validators.project_validator import validate_diagram


EXAMPLES_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'examples')


def test_example_1_structure():
    ex1_dir = os.path.join(EXAMPLES_DIR, '01_esp32_temperature_monitor')
    assert os.path.exists(os.path.join(ex1_dir, 'sketch.ino'))
    assert os.path.exists(os.path.join(ex1_dir, 'diagram.json'))
    assert os.path.exists(os.path.join(ex1_dir, 'libraries.txt'))
    assert os.path.exists(os.path.join(ex1_dir, 'wokwi.toml'))
    assert os.path.exists(os.path.join(ex1_dir, 'README.md'))

    with open(os.path.join(ex1_dir, 'diagram.json')) as f:
        diag = json.load(f)
    res = validate_diagram(diag)
    assert res.valid, f"Example 1 diagram invalid: {res.errors}"

    with open(os.path.join(ex1_dir, 'sketch.ino')) as f:
        sketch = f.read()
    assert 'setup()' in sketch
    assert 'loop()' in sketch
    assert 'DHTPIN 4' in sketch
    assert 'LED_PIN 2' in sketch


def test_example_2_structure():
    ex2_dir = os.path.join(EXAMPLES_DIR, '02_ultrasonic_distance_warning')
    assert os.path.exists(os.path.join(ex2_dir, 'sketch.ino'))
    assert os.path.exists(os.path.join(ex2_dir, 'diagram.json'))
    assert os.path.exists(os.path.join(ex2_dir, 'libraries.txt'))
    assert os.path.exists(os.path.join(ex2_dir, 'wokwi.toml'))
    assert os.path.exists(os.path.join(ex2_dir, 'README.md'))

    with open(os.path.join(ex2_dir, 'diagram.json')) as f:
        diag = json.load(f)
    res = validate_diagram(diag)
    assert res.valid, f"Example 2 diagram invalid: {res.errors}"

    with open(os.path.join(ex2_dir, 'sketch.ino')) as f:
        sketch = f.read()
    assert 'setup()' in sketch
    assert 'loop()' in sketch
    assert 'TRIG_PIN 5' in sketch
    assert 'ECHO_PIN 18' in sketch
    assert 'BUZZER_PIN 19' in sketch


def test_example_3_structure():
    ex3_dir = os.path.join(EXAMPLES_DIR, '03_environmental_monitor')
    assert os.path.exists(os.path.join(ex3_dir, 'sketch.ino'))
    assert os.path.exists(os.path.join(ex3_dir, 'diagram.json'))
    assert os.path.exists(os.path.join(ex3_dir, 'libraries.txt'))
    assert os.path.exists(os.path.join(ex3_dir, 'wokwi.toml'))
    assert os.path.exists(os.path.join(ex3_dir, 'README.md'))

    with open(os.path.join(ex3_dir, 'diagram.json')) as f:
        diag = json.load(f)
    res = validate_diagram(diag)
    assert res.valid, f"Example 3 diagram invalid: {res.errors}"

    with open(os.path.join(ex3_dir, 'sketch.ino')) as f:
        sketch = f.read()
    assert 'setup()' in sketch
    assert 'loop()' in sketch
    assert 'DHTPIN 4' in sketch
    assert 'POT_PIN 34' in sketch
    assert 'LED_PIN 2' in sketch
    assert 'BUZZER_PIN 19' in sketch


if __name__ == '__main__':
    test_example_1_structure()
    print("PASS: Example 1 structure and diagram validation")
    test_example_2_structure()
    print("PASS: Example 2 structure and diagram validation")
    test_example_3_structure()
    print("PASS: Example 3 structure and diagram validation")
    print("\nAll example integration tests PASSED!")
