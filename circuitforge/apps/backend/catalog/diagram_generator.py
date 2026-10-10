"""
CircuitForge AI - Diagram Generator
Generates Wokwi-compatible diagram.json from a validated ProjectSpec.
Uses deterministic templates — does NOT rely on unconstrained AI output.
"""
from __future__ import annotations
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from schemas import ProjectSpec, ComponentInstance, Connection, PinAssignment
from catalog.components import CATALOG


# ── Wokwi attribute helpers ────────────────────────────────────────────────────

def _resistor_attrs(value: str = "220") -> dict:
    return {"resistance": value}


def _led_attrs(color: str = "red") -> dict:
    return {"color": color}


def _dht22_attrs() -> dict:
    return {"temperature": "25", "humidity": "50"}


def _hcsr04_attrs() -> dict:
    return {"distance": "100"}


def _buzzer_attrs() -> dict:
    return {"volume": "0.5"}


def _potentiometer_attrs(value: str = "0.5") -> dict:
    return {"value": value}


COMPONENT_ATTRS: dict[str, callable] = {
    "resistor_220": lambda inst: _resistor_attrs("220"),
    "resistor_10k": lambda inst: _resistor_attrs("10000"),
    "led_red": lambda inst: _led_attrs("red"),
    "dht22": lambda inst: _dht22_attrs(),
    "hc_sr04": lambda inst: _hcsr04_attrs(),
    "buzzer": lambda inst: _buzzer_attrs(),
    "push_button": lambda inst: {},
    "potentiometer_10k": lambda inst: _potentiometer_attrs(),
}

# Layout positions for parts — space them horizontally
X_STEP = 150
Y_BOARD = 100
Y_COMPONENTS = 350


def generate_diagram(spec: ProjectSpec) -> dict:
    """
    Generate a Wokwi-compatible diagram.json from a ProjectSpec.
    Returns a dict that can be serialized to JSON.
    """
    parts: list[dict] = []
    connections: list[list[str]] = []

    # ── Board ─────────────────────────────────────────────────────────────────
    board_wokwi_id = "wokwi-esp32-devkit-v1"
    parts.append({
        "id": "board",
        "type": board_wokwi_id,
        "top": Y_BOARD,
        "left": 200,
        "attrs": {}
    })

    # ── Components ────────────────────────────────────────────────────────────
    x = 50
    for inst in spec.components:
        cat = CATALOG.get(inst.catalog_id)
        if cat is None:
            continue  # skip unknown (already validated)

        attr_fn = COMPONENT_ATTRS.get(inst.catalog_id, lambda i: {})
        attrs = attr_fn(inst)
        if inst.catalog_id == "resistor_220" and inst.value:
            attrs = {"resistance": inst.value}
        elif inst.catalog_id == "resistor_10k" and inst.value:
            attrs = {"resistance": inst.value}

        parts.append({
            "id": inst.instance_id,
            "type": cat.wokwi_id,
            "top": Y_COMPONENTS,
            "left": x,
            "attrs": attrs,
        })
        x += X_STEP

    # ── Connections ───────────────────────────────────────────────────────────
    # Build from spec.connections
    for conn in spec.connections:
        from_ref = f"{conn.from_component}:{conn.from_pin}"
        to_ref = f"{conn.to_component}:{conn.to_pin}"
        connections.append([from_ref, to_ref, conn.wire_color, []])

    # If no explicit connections defined, generate from pin assignments
    if not connections and spec.pin_assignments:
        connections = _generate_connections_from_pin_assignments(spec)

    diagram = {
        "version": 1,
        "author": "CircuitForge AI",
        "editor": "wokwi",
        "parts": parts,
        "connections": connections,
    }
    return diagram


def _generate_connections_from_pin_assignments(spec: ProjectSpec) -> list[list]:
    """
    Fallback: generate Wokwi connections from pin assignment metadata.
    Handles common patterns for DHT22, LED+Resistor, HC-SR04, Buzzer.
    """
    connections: list[list] = []
    instance_map: dict[str, str] = {inst.instance_id: inst.catalog_id for inst in spec.components}

    for pa in spec.pin_assignments:
        gpio_pin_str = f"GPIO{pa.gpio_pin}"
        inst_id = pa.component_instance
        comp_pin = pa.component_pin
        catalog_id = instance_map.get(inst_id, "")

        color = "green"
        if "gnd" in comp_pin.lower() or comp_pin.lower() in ("k", "-", "gnd"):
            color = "black"
        elif "vcc" in comp_pin.lower() or comp_pin.lower() in ("vcc", "+", "3v3"):
            color = "red"

        # Board GPIO to component pin
        connections.append([
            f"board:{gpio_pin_str}", f"{inst_id}:{comp_pin}", color, []
        ])

    # Add power/ground connections for all components
    for inst in spec.components:
        cat = CATALOG.get(inst.catalog_id)
        if cat is None:
            continue
        for pin in cat.pins:
            if pin.pin_type == "power" and pin.name.upper() in ("VCC", "3V3", "VIN"):
                connections.append([
                    f"board:3V3", f"{inst.instance_id}:{pin.name}", "red", []
                ])
            elif pin.pin_type == "ground" and pin.name.upper() == "GND":
                connections.append([
                    f"board:GND", f"{inst.instance_id}:{pin.name}", "black", []
                ])

    return connections
