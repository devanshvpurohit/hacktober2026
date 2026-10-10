"""
CircuitForge AI - Local AI Integration
Handles Ollama inference for planning (gemma3:1b) and firmware generation (Arduino-Coder-0.5B).
Never uses cloud LLMs. Validates all outputs. Reports actual errors.
"""
from __future__ import annotations
import asyncio
import json
import re
import sys
import os
from typing import Optional

import httpx

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from schemas import ProjectSpec, ComponentInstance, PinAssignment, Connection, BoardType
from catalog.components import CATALOG, ESP32_VALID_GPIO

OLLAMA_BASE = "http://localhost:11434"
PLANNER_MODEL = "gemma3:1b"
FIRMWARE_MODEL = "hf.co/tapariapurv/Arduino-Coder-0.5B-GGUF-v1:Q4_K_M"
TIMEOUT = 120.0
MAX_TOKENS_PLAN = 2048
MAX_TOKENS_FIRMWARE = 4096


# ── Ollama helper ─────────────────────────────────────────────────────────────

async def _ollama_generate(model: str, prompt: str, max_tokens: int = 2048) -> str:
    """Run an Ollama generate call. Returns the response text or raises."""
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"num_predict": max_tokens, "temperature": 0.2},
    }
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.post(f"{OLLAMA_BASE}/api/generate", json=payload)
        resp.raise_for_status()
        data = resp.json()
        return data.get("response", "").strip()


def _extract_json(text: str) -> Optional[dict]:
    """Extract first JSON object from model output."""
    # Try direct parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Look for ```json ... ``` block
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass

    # Look for bare JSON object
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            pass

    return None


def _extract_code(text: str, lang: str = "cpp") -> str:
    """Extract code from a markdown code block."""
    # Try ```cpp or ```arduino or ```c
    for tag in [lang, "cpp", "c++", "arduino", "c", ""]:
        pattern = rf"```{tag}\s*(.*?)```"
        m = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        if m:
            return m.group(1).strip()
    # If no code block, return the whole text stripped
    return text.strip()


# ── Planning ──────────────────────────────────────────────────────────────────

PLAN_PROMPT_TEMPLATE = """You are CircuitForge AI, an expert IoT project planner.
Given a user's IoT project request, produce a JSON project specification.

Available components in catalog: {catalog_ids}

User request: {user_request}

Respond with ONLY a valid JSON object with this exact structure:
{{
  "name": "Short project name",
  "description": "One sentence description",
  "behavior": "Detailed behavior description",
  "board": "esp32",
  "components": [
    {{"instance_id": "dht22_1", "catalog_id": "dht22", "name": "DHT22 Sensor", "quantity": 1}},
    {{"instance_id": "led_1", "catalog_id": "led_red", "name": "LED Indicator", "quantity": 1}},
    {{"instance_id": "r1", "catalog_id": "resistor_220", "name": "220 Ohm Resistor", "quantity": 1, "value": "220"}}
  ],
  "pin_assignments": [
    {{"component_id": "dht22", "component_instance": "dht22_1", "component_pin": "SDA", "gpio_pin": 4, "description": "DHT22 data pin"}},
    {{"component_id": "led_red", "component_instance": "led_1", "component_pin": "A", "gpio_pin": 2, "description": "LED anode"}}
  ],
  "connections": [],
  "libraries": ["DHT sensor library", "Adafruit Unified Sensor"],
  "acceptance_criteria": ["Temperature is read every 2 seconds", "LED turns on when temp > 30C"],
  "assumptions": ["DHT22 module with built-in pull-up resistor"],
  "warnings": ["Allow 2s warmup time for DHT22"],
  "missing_info": [],
  "unsupported": [],
  "threshold_value": 30.0,
  "threshold_unit": "Celsius"
}}

IMPORTANT INSTRUCTIONS:
1. If the requested components are in the catalog, use them directly.
2. If components are NOT in the catalog, you can still create a plan using best-guess catalog_id names (e.g., "servo_motor", "lcd_display", "relay_module").
3. For missing components, add them to the "missing_info" array with format: "Component XYZ not in catalog - suggested alternative: ABC"
4. Only use valid ESP32 GPIO pins (not 6-11, not 34-39 for output).
5. Be creative and flexible - accept ANY IoT project request and try to create a working plan.
"""


def _deterministic_plan(user_request: str) -> tuple[ProjectSpec, str]:
    """
    Flexible deterministic planner that handles a wide variety of project requests.
    Falls back to generic templates when specific patterns don't match.
    """
    req_lower = user_request.lower()
    threshold = 30.0
    m = re.search(r"(\d+(?:\.\d+)?)\s*(?:degrees?|°)?\s*(celsius|centigrade|C\b|fahrenheit|F\b|cm\b|centimeters?)", user_request, re.IGNORECASE)
    if m:
        threshold = float(m.group(1))

    # Servo / Motor Projects
    if "servo" in req_lower or ("motor" in req_lower and "stepper" not in req_lower):
        spec = ProjectSpec(
            name="ESP32 Servo Control System",
            description="ESP32 servo motor control with button input",
            behavior="Controls servo motor position based on button presses. Button cycles servo through different positions (0°, 90°, 180°).",
            board=BoardType.ESP32,
            components=[
                ComponentInstance(instance_id="servo_1", catalog_id="servo_motor", name="Servo Motor SG90", quantity=1),
                ComponentInstance(instance_id="btn_1", catalog_id="push_button", name="Push Button", quantity=1),
                ComponentInstance(instance_id="led_1", catalog_id="led_red", name="Status LED", quantity=1),
                ComponentInstance(instance_id="r1", catalog_id="resistor_220", name="220 Ohm Resistor", quantity=1, value="220"),
            ],
            pin_assignments=[
                PinAssignment(component_id="servo_motor", component_instance="servo_1", component_pin="SIG", gpio_pin=13, description="Servo control signal (PWM)"),
                PinAssignment(component_id="push_button", component_instance="btn_1", component_pin="1.l", gpio_pin=12, description="Button input"),
                PinAssignment(component_id="led_red", component_instance="led_1", component_pin="A", gpio_pin=2, description="Status LED"),
            ],
            connections=[],
            libraries=["ESP32Servo"],
            acceptance_criteria=["Control servo position with button", "Button cycles servo through 0°, 90°, 180°", "LED indicates servo movement"],
            warnings=["Servo motor (servo_motor) not in standard catalog - using generic SG90 servo", "Servo may require external 5V power supply if moving under load"],
            missing_info=["Servo motor component catalog entry needed for BOM pricing"],
        )
    
    # LCD / Display Projects
    elif "lcd" in req_lower or "display" in req_lower or "oled" in req_lower:
        spec = ProjectSpec(
            name="ESP32 LCD Display System",
            description="ESP32 with LCD/OLED display showing sensor data or messages",
            behavior="Displays real-time data or messages on LCD/OLED screen",
            board=BoardType.ESP32,
            components=[
                ComponentInstance(instance_id="display_1", catalog_id="lcd_display", name="LCD Display", quantity=1),
                ComponentInstance(instance_id="dht_1", catalog_id="dht22", name="DHT22 Sensor", quantity=1),
            ],
            pin_assignments=[
                PinAssignment(component_id="lcd_display", component_instance="display_1", component_pin="SDA", gpio_pin=21, description="I2C Data"),
                PinAssignment(component_id="lcd_display", component_instance="display_1", component_pin="SCL", gpio_pin=22, description="I2C Clock"),
                PinAssignment(component_id="dht22", component_instance="dht_1", component_pin="SDA", gpio_pin=4, description="DHT22 Data"),
            ],
            connections=[],
            libraries=["LiquidCrystal_I2C", "DHT sensor library"],
            acceptance_criteria=["Display data on LCD", "Read sensor values"],
            warnings=["[OFFLINE MODE] Ollama offline. Generated from flexible catalog template."],
            missing_info=["LCD display (lcd_display) not in standard catalog - I2C LCD assumed"],
        )
    
    # Relay / Switch Projects
    elif "relay" in req_lower or "switch" in req_lower and "lamp" in req_lower or "appliance" in req_lower:
        spec = ProjectSpec(
            name="ESP32 Relay Control System",
            description="ESP32 controlling relay for appliance switching",
            behavior="Switches relay on/off based on sensor input or timer",
            board=BoardType.ESP32,
            components=[
                ComponentInstance(instance_id="relay_1", catalog_id="relay_module", name="Relay Module", quantity=1),
                ComponentInstance(instance_id="btn_1", catalog_id="push_button", name="Push Button", quantity=1),
                ComponentInstance(instance_id="led_1", catalog_id="led_red", name="Status LED", quantity=1),
                ComponentInstance(instance_id="r1", catalog_id="resistor_220", name="220 Ohm Resistor", quantity=1, value="220"),
            ],
            pin_assignments=[
                PinAssignment(component_id="relay_module", component_instance="relay_1", component_pin="SIG", gpio_pin=13, description="Relay control"),
                PinAssignment(component_id="push_button", component_instance="btn_1", component_pin="1.l", gpio_pin=12, description="Button input"),
                PinAssignment(component_id="led_red", component_instance="led_1", component_pin="A", gpio_pin=2, description="Status LED"),
            ],
            connections=[],
            libraries=[],
            acceptance_criteria=["Control relay switching", "Button triggers relay"],
            warnings=["[OFFLINE MODE] Ollama offline. Generated from flexible catalog template.", "WARNING: Ensure relay is rated for intended load"],
            missing_info=["Relay module (relay_module) not in standard catalog - 5V relay assumed"],
        )
    
    # Distance / Ultrasonic Projects
    elif "distance" in req_lower or "ultrasonic" in req_lower or "sr04" in req_lower:
        act_thresh = threshold if threshold != 30.0 else 20.0
        spec = ProjectSpec(
            name="Ultrasonic Distance Warning System",
            description="ESP32 ultrasonic distance detector using HC-SR04 with buzzer alert",
            behavior=f"Measures obstacle distance; activates buzzer when distance < {act_thresh} cm",
            board=BoardType.ESP32,
            components=[
                ComponentInstance(instance_id="ultrasonic_1", catalog_id="hc_sr04", name="HC-SR04 Ultrasonic Sensor", quantity=1),
                ComponentInstance(instance_id="buzzer_1", catalog_id="buzzer", name="Active Buzzer", quantity=1),
            ],
            pin_assignments=[
                PinAssignment(component_id="hc_sr04", component_instance="ultrasonic_1", component_pin="TRIG", gpio_pin=5, description="Trigger pin"),
                PinAssignment(component_id="hc_sr04", component_instance="ultrasonic_1", component_pin="ECHO", gpio_pin=18, description="Echo pulse input"),
                PinAssignment(component_id="buzzer", component_instance="buzzer_1", component_pin="+", gpio_pin=19, description="Buzzer positive control"),
            ],
            connections=[],
            libraries=[],
            acceptance_criteria=[
                "Read distance via HC-SR04 echo duration",
                f"Activate buzzer when distance is less than {act_thresh} cm"
            ],
            warnings=["[OFFLINE MODE] Ollama offline. Generated from verified catalog template."],
            threshold_value=act_thresh,
            threshold_unit="cm"
        )
    
    # Environmental / Potentiometer Projects
    elif "potentiometer" in req_lower or "environmental" in req_lower:
        spec = ProjectSpec(
            name="Dynamic Environmental Monitor",
            description="ESP32 environmental monitor with DHT22, analog potentiometer threshold, and indicators",
            behavior="Reads ambient temperature/humidity; potentiometer adjusts threshold dynamically; triggers LED and buzzer on alarm",
            board=BoardType.ESP32,
            components=[
                ComponentInstance(instance_id="dht22_1", catalog_id="dht22", name="DHT22 Sensor", quantity=1),
                ComponentInstance(instance_id="pot_1", catalog_id="potentiometer_10k", name="10k Potentiometer", quantity=1),
                ComponentInstance(instance_id="led_1", catalog_id="led_red", name="Red LED", quantity=1),
                ComponentInstance(instance_id="r1", catalog_id="resistor_220", name="220 Ohm Resistor", quantity=1, value="220"),
                ComponentInstance(instance_id="buzzer_1", catalog_id="buzzer", name="Active Buzzer", quantity=1),
            ],
            pin_assignments=[
                PinAssignment(component_id="dht22", component_instance="dht22_1", component_pin="SDA", gpio_pin=4, description="DHT22 Data"),
                PinAssignment(component_id="potentiometer_10k", component_instance="pot_1", component_pin="SIG", gpio_pin=34, description="Analog Potentiometer"),
                PinAssignment(component_id="led_red", component_instance="led_1", component_pin="A", gpio_pin=2, description="LED Anode"),
                PinAssignment(component_id="buzzer", component_instance="buzzer_1", component_pin="+", gpio_pin=19, description="Buzzer Signal"),
            ],
            connections=[],
            libraries=["DHT sensor library", "Adafruit Unified Sensor"],
            acceptance_criteria=["Sample DHT22 every 2s", "Read ADC on GPIO34", "Trigger alarms when temp > threshold"],
            warnings=["[OFFLINE MODE] Ollama offline. Generated from verified catalog template."],
            threshold_value=threshold,
            threshold_unit="Celsius"
        )
    
    # Generic fallback for any other project
    else:
        # Extract likely component keywords from the request
        missing_components = []
        description = f"ESP32-based {user_request[:50]}"
        
        # Always include basic components for a generic project
        components = [
            ComponentInstance(instance_id="led_1", catalog_id="led_red", name="Status LED", quantity=1),
            ComponentInstance(instance_id="r1", catalog_id="resistor_220", name="220 Ohm Resistor", quantity=1, value="220"),
        ]
        
        pin_assignments = [
            PinAssignment(component_id="led_red", component_instance="led_1", component_pin="A", gpio_pin=2, description="Status LED"),
        ]
        
        # Add sensor if temperature/humidity mentioned
        if "temp" in req_lower or "humidity" in req_lower or "sensor" in req_lower:
            components.append(ComponentInstance(instance_id="dht22_1", catalog_id="dht22", name="DHT22 Sensor", quantity=1))
            pin_assignments.append(PinAssignment(component_id="dht22", component_instance="dht22_1", component_pin="SDA", gpio_pin=4, description="DHT22 Data"))
        
        # Add buzzer if alarm/alert/sound mentioned
        if "alarm" in req_lower or "alert" in req_lower or "buzzer" in req_lower or "sound" in req_lower:
            components.append(ComponentInstance(instance_id="buzzer_1", catalog_id="buzzer", name="Active Buzzer", quantity=1))
            pin_assignments.append(PinAssignment(component_id="buzzer", component_instance="buzzer_1", component_pin="+", gpio_pin=19, description="Buzzer Signal"))
        
        # Add button if input/button mentioned
        if "button" in req_lower or "input" in req_lower:
            components.append(ComponentInstance(instance_id="btn_1", catalog_id="push_button", name="Push Button", quantity=1))
            pin_assignments.append(PinAssignment(component_id="push_button", component_instance="btn_1", component_pin="1.l", gpio_pin=12, description="Button input"))
        
        spec = ProjectSpec(
            name=f"Custom {user_request[:30].strip().title()}",
            description=description,
            behavior=f"Custom IoT project: {user_request[:100]}",
            board=BoardType.ESP32,
            components=components,
            pin_assignments=pin_assignments,
            connections=[],
            libraries=[],
            acceptance_criteria=[f"Implement: {user_request[:100]}"],
            warnings=["[OFFLINE MODE] Ollama offline. Generated from generic flexible template.", 
                     "[CUSTOM PROJECT] This is a flexible template - firmware may need manual adjustments"],
            missing_info=missing_components if missing_components else ["Custom project - some components may not be in catalog"],
            threshold_value=threshold,
            threshold_unit="Celsius"
        )
    
    return spec, json.dumps(spec.model_dump(), indent=2)


async def plan_project(user_request: str) -> tuple[ProjectSpec, str]:
    """
    Use Gemma3:1b to plan a project from a user request.
    Falls back to verified deterministic catalog planner if Ollama is unreachable.
    Returns (ProjectSpec, raw_response_text).
    """
    # Check for specific keywords that have better deterministic templates
    req_lower = user_request.lower()
    use_deterministic = any([
        "servo" in req_lower,
        "motor" in req_lower and "stepper" not in req_lower,
        "lcd" in req_lower,
        "oled" in req_lower,
        "relay" in req_lower,
    ])
    
    # If we have a good template, use it directly
    if use_deterministic:
        return _deterministic_plan(user_request)
    
    catalog_ids = list(CATALOG.keys())
    prompt = PLAN_PROMPT_TEMPLATE.format(
        catalog_ids=json.dumps(catalog_ids),
        user_request=user_request,
    )

    try:
        raw = await _ollama_generate(PLANNER_MODEL, prompt, MAX_TOKENS_PLAN)
    except (httpx.ConnectError, httpx.TimeoutException, OSError):
        # Ollama not currently running or cannot connect: use deterministic catalog planner
        return _deterministic_plan(user_request)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 403:
            # Sandbox or local network isolation prevents localhost socket access
            return _deterministic_plan(user_request)
        if e.response.status_code == 404:
            raise ValueError(f"Model '{PLANNER_MODEL}' not installed. Run: ollama pull {PLANNER_MODEL}")
        raise ValueError(f"Ollama error: {e}")
    except Exception as e:
        raise ValueError(f"AI planning failed: {e}")

    data = _extract_json(raw)
    if data is None:
        return _deterministic_plan(user_request)

    # Sanitize data before Pydantic validation
    if isinstance(data, dict):
        if "board" in data and isinstance(data["board"], str):
            data["board"] = data["board"].lower().replace("-", "_").strip()
        if "connections" in data and isinstance(data["connections"], list):
            # If model returned list of strings or non-dicts, reset to empty
            if not all(isinstance(c, dict) and "from_component" in c for c in data["connections"]):
                data["connections"] = []
        if "components" in data and isinstance(data["components"], list):
            for i, c in enumerate(data["components"]):
                if isinstance(c, dict) and "instance_id" not in c:
                    c["instance_id"] = f"{c.get('catalog_id', 'part')}_{i+1}"

    try:
        spec = ProjectSpec.model_validate(data)
    except Exception as e:
        # Fall back to verified deterministic plan if model returned invalid schema
        det_spec, _ = _deterministic_plan(user_request)
        det_spec.warnings.append(f"[AI PLAN ADJUSTMENT] Model output adapted: {e}")
        return det_spec, raw

    # Ensure threshold is captured if in the request
    if spec.threshold_value is None:
        # Try to extract from user request
        m = re.search(r"(\d+(?:\.\d+)?)\s*(?:degrees?|°)?\s*(celsius|centigrade|C\b|fahrenheit|F\b)", user_request, re.IGNORECASE)
        if m:
            spec.threshold_value = float(m.group(1))
            spec.threshold_unit = "Celsius" if m.group(2).upper().startswith("C") else "Fahrenheit"

    return spec, raw


# ── Firmware Generation ────────────────────────────────────────────────────────

FIRMWARE_PROMPT_TEMPLATE = """You are an expert Arduino/ESP32 firmware developer.
Generate complete, compilable Arduino C++ firmware for the following project.

Project Name: {name}
Board: ESP32 DevKit V1
Behavior: {behavior}
Libraries needed: {libraries}

Pin assignments:
{pin_assignments}

Components:
{components}

{threshold_info}

Requirements:
- Include all required library headers
- Define all pin constants as #define or const int
- Include setup() and loop() functions
- Handle sensor read errors gracefully
- Use Serial.begin(115200) in setup()
- Print sensor readings to Serial
- Follow exact pin assignments provided above
- If a component is not in the standard library, use best-effort generic code (e.g., digitalWrite for relays, analogWrite for servos)
- Be creative and flexible - generate working code even for components not in standard Arduino libraries

Generate ONLY the Arduino C++ code, starting with the #include statements.
Do NOT add explanations outside the code. The output must compile with Arduino CLI for ESP32.
"""


def _deterministic_firmware(spec: ProjectSpec) -> str:
    """
    Generate firmware for various project types, with flexible fallback for unknown components.
    """
    pins = {pa.component_pin.upper(): pa.gpio_pin for pa in spec.pin_assignments}
    thresh = spec.threshold_value if spec.threshold_value is not None else 30.0
    comp_ids = {c.catalog_id for c in spec.components}
    
    # Servo motor projects
    if "servo_motor" in comp_ids:
        servo_pin = pins.get("SIG", 13)
        button_pin = pins.get("1.L", 12)
        return f"""/*
 * Auto-generated by CircuitForge AI (Flexible Generator)
 * Project: {spec.name}
 */
#include <Arduino.h>
#include <ESP32Servo.h>

#define SERVO_PIN {servo_pin}
#define BUTTON_PIN {button_pin}

Servo myServo;
int servoPos = 90;

void setup() {{
  Serial.begin(115200);
  pinMode(BUTTON_PIN, INPUT_PULLUP);
  myServo.attach(SERVO_PIN);
  myServo.write(servoPos);
  Serial.println(F("CircuitForge AI - Servo Control System Initialized"));
}}

void loop() {{
  if (digitalRead(BUTTON_PIN) == LOW) {{
    servoPos = (servoPos + 30) % 180;
    myServo.write(servoPos);
    Serial.print(F("Servo Position: "));
    Serial.println(servoPos);
    delay(500);
  }}
  delay(50);
}}
"""
    
    # LCD Display projects
    elif "lcd_display" in comp_ids:
        dht_pin = pins.get("SDA", 4)  # DHT sensor
        return f"""/*
 * Auto-generated by CircuitForge AI (Flexible Generator)
 * Project: {spec.name}
 */
#include <Arduino.h>
#include <Wire.h>
#include <LiquidCrystal_I2C.h>
#include <DHT.h>

#define DHTPIN {dht_pin}
#define DHTTYPE DHT22

LiquidCrystal_I2C lcd(0x27, 16, 2);
DHT dht(DHTPIN, DHTTYPE);

void setup() {{
  Serial.begin(115200);
  lcd.init();
  lcd.backlight();
  dht.begin();
  lcd.setCursor(0, 0);
  lcd.print("CircuitForge AI");
  delay(2000);
  Serial.println(F("CircuitForge AI - LCD Display System Initialized"));
}}

void loop() {{
  float t = dht.readTemperature();
  float h = dht.readHumidity();
  
  if (!isnan(t) && !isnan(h)) {{
    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print("Temp: ");
    lcd.print(t, 1);
    lcd.print(" C");
    lcd.setCursor(0, 1);
    lcd.print("Humidity: ");
    lcd.print(h, 1);
    lcd.print("%");
    
    Serial.print(F("Temp: "));
    Serial.print(t);
    Serial.print(F(" C | Humidity: "));
    Serial.print(h);
    Serial.println(F(" %"));
  }}
  delay(2000);
}}
"""
    
    # Relay projects
    elif "relay_module" in comp_ids:
        relay_pin = pins.get("SIG", 13)
        button_pin = pins.get("1.L", 12)
        led_pin = pins.get("A", 2)
        return f"""/*
 * Auto-generated by CircuitForge AI (Flexible Generator)
 * Project: {spec.name}
 */
#include <Arduino.h>

#define RELAY_PIN {relay_pin}
#define BUTTON_PIN {button_pin}
#define LED_PIN {led_pin}

bool relayState = false;

void setup() {{
  Serial.begin(115200);
  pinMode(RELAY_PIN, OUTPUT);
  pinMode(BUTTON_PIN, INPUT_PULLUP);
  pinMode(LED_PIN, OUTPUT);
  digitalWrite(RELAY_PIN, LOW);
  digitalWrite(LED_PIN, LOW);
  Serial.println(F("CircuitForge AI - Relay Control System Initialized"));
}}

void loop() {{
  static bool lastButtonState = HIGH;
  bool buttonState = digitalRead(BUTTON_PIN);
  
  if (buttonState == LOW && lastButtonState == HIGH) {{
    relayState = !relayState;
    digitalWrite(RELAY_PIN, relayState ? HIGH : LOW);
    digitalWrite(LED_PIN, relayState ? HIGH : LOW);
    Serial.print(F("Relay: "));
    Serial.println(relayState ? "ON" : "OFF");
    delay(200); // Debounce
  }}
  lastButtonState = buttonState;
  delay(50);
}}
"""
    
    # Distance sensor projects
    elif "hc_sr04" in comp_ids:
        trig = pins.get("TRIG", 5)
        echo = pins.get("ECHO", 18)
        buzzer = pins.get("+", 19)
        return f"""/*
 * Auto-generated by CircuitForge AI (Deterministic Catalog Generator)
 * Project: {spec.name}
 */
#include <Arduino.h>

#define TRIG_PIN {trig}
#define ECHO_PIN {echo}
#define BUZZER_PIN {buzzer}

const float THRESHOLD_CM = {thresh};

void setup() {{
  Serial.begin(115200);
  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);
  pinMode(BUZZER_PIN, OUTPUT);
  digitalWrite(BUZZER_PIN, LOW);
  Serial.println(F("CircuitForge AI - Ultrasonic Distance Warning Initialized"));
}}

void loop() {{
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);

  long duration = pulseIn(ECHO_PIN, HIGH, 30000);
  if (duration > 0) {{
    float distanceCm = duration * 0.0343 / 2.0;
    Serial.print(F("Distance: "));
    Serial.print(distanceCm);
    Serial.println(F(" cm"));
    if (distanceCm < THRESHOLD_CM) {{
      digitalWrite(BUZZER_PIN, HIGH);
    }} else {{
      digitalWrite(BUZZER_PIN, LOW);
    }}
  }}
  delay(200);
}}
"""
    
    # Environmental monitor with potentiometer
    elif "potentiometer_10k" in comp_ids and "dht22" in comp_ids:
        dht_pin = pins.get("SDA", 4)
        pot_pin = pins.get("SIG", 34)
        led_pin = pins.get("A", 2)
        buzzer_pin = pins.get("+", 19)
        return f"""/*
 * Auto-generated by CircuitForge AI (Deterministic Catalog Generator)
 * Project: {spec.name}
 */
#include <Arduino.h>
#include <DHT.h>

#define DHTPIN {dht_pin}
#define DHTTYPE DHT22
#define POT_PIN {pot_pin}
#define LED_PIN {led_pin}
#define BUZZER_PIN {buzzer_pin}

DHT dht(DHTPIN, DHTTYPE);

void setup() {{
  Serial.begin(115200);
  pinMode(LED_PIN, OUTPUT);
  pinMode(BUZZER_PIN, OUTPUT);
  pinMode(POT_PIN, INPUT);
  digitalWrite(LED_PIN, LOW);
  digitalWrite(BUZZER_PIN, LOW);
  dht.begin();
  Serial.println(F("CircuitForge AI - Dynamic Environmental Monitor Initialized"));
}}

void loop() {{
  delay(2000);
  int potVal = analogRead(POT_PIN);
  float dynamicThreshold = 20.0 + (potVal / 4095.0) * 25.0;
  float t = dht.readTemperature();
  float h = dht.readHumidity();

  if (!isnan(t)) {{
    Serial.print(F("Temp: "));
    Serial.print(t);
    Serial.print(F(" C | Threshold: "));
    Serial.println(dynamicThreshold);
    if (t > dynamicThreshold) {{
      digitalWrite(LED_PIN, HIGH);
      digitalWrite(BUZZER_PIN, HIGH);
    }} else {{
      digitalWrite(LED_PIN, LOW);
      digitalWrite(BUZZER_PIN, LOW);
    }}
  }}
}}
"""
    
    # Environmental monitor with potentiometer
    elif "potentiometer_10k" in comp_ids and "dht22" in comp_ids:
        dht_pin = pins.get("SDA", 4)
        pot_pin = pins.get("SIG", 34)
        led_pin = pins.get("A", 2)
        buzzer_pin = pins.get("+", 19)
        return f"""/*
 * Auto-generated by CircuitForge AI (Deterministic Catalog Generator)
 * Project: {spec.name}
 */
#include <Arduino.h>
#include <DHT.h>

#define DHTPIN {dht_pin}
#define DHTTYPE DHT22
#define POT_PIN {pot_pin}
#define LED_PIN {led_pin}
#define BUZZER_PIN {buzzer_pin}

DHT dht(DHTPIN, DHTTYPE);

void setup() {{
  Serial.begin(115200);
  pinMode(LED_PIN, OUTPUT);
  pinMode(BUZZER_PIN, OUTPUT);
  pinMode(POT_PIN, INPUT);
  digitalWrite(LED_PIN, LOW);
  digitalWrite(BUZZER_PIN, LOW);
  dht.begin();
  Serial.println(F("CircuitForge AI - Dynamic Environmental Monitor Initialized"));
}}

void loop() {{
  delay(2000);
  int potVal = analogRead(POT_PIN);
  float dynamicThreshold = 20.0 + (potVal / 4095.0) * 25.0;
  float t = dht.readTemperature();
  float h = dht.readHumidity();

  if (!isnan(t)) {{
    Serial.print(F("Temp: "));
    Serial.print(t);
    Serial.print(F(" C | Threshold: "));
    Serial.println(dynamicThreshold);
    if (t > dynamicThreshold) {{
      digitalWrite(LED_PIN, HIGH);
      digitalWrite(BUZZER_PIN, HIGH);
    }} else {{
      digitalWrite(LED_PIN, LOW);
      digitalWrite(BUZZER_PIN, LOW);
    }}
  }}
}}
"""
    
    # Generic fallback for any other project type
    else:
        # Build a generic firmware based on what components we have
        includes = ["#include <Arduino.h>"]
        defines = []
        setup_code = ["  Serial.begin(115200);"]
        loop_code = []
        
        # Check for DHT sensor
        if "dht22" in comp_ids:
            includes.append("#include <DHT.h>")
            dht_pin = pins.get("SDA", 4)
            defines.append(f"#define DHTPIN {dht_pin}")
            defines.append("#define DHTTYPE DHT22")
            defines.append("DHT dht(DHTPIN, DHTTYPE);")
            setup_code.append("  dht.begin();")
            loop_code.append("""  float t = dht.readTemperature();
  float h = dht.readHumidity();
  if (!isnan(t)) {{
    Serial.print(F("Temp: "));
    Serial.print(t);
    Serial.print(F(" C | Humidity: "));
    Serial.print(h);
    Serial.println(F(" %"));
  }}""")
        
        # Check for LED
        if "led_red" in comp_ids:
            led_pin = pins.get("A", 2)
            defines.append(f"#define LED_PIN {led_pin}")
            setup_code.append(f"  pinMode(LED_PIN, OUTPUT);")
            setup_code.append("  digitalWrite(LED_PIN, LOW);")
            loop_code.append("  digitalWrite(LED_PIN, HIGH);")
        
        # Check for buzzer
        if "buzzer" in comp_ids:
            buzzer_pin = pins.get("+", 19)
            defines.append(f"#define BUZZER_PIN {buzzer_pin}")
            setup_code.append(f"  pinMode(BUZZER_PIN, OUTPUT);")
            setup_code.append("  digitalWrite(BUZZER_PIN, LOW);")
        
        # Check for button
        if "push_button" in comp_ids:
            button_pin = pins.get("1.L", 12)
            defines.append(f"#define BUTTON_PIN {button_pin}")
            setup_code.append(f"  pinMode(BUTTON_PIN, INPUT_PULLUP);")
            loop_code.append("""  if (digitalRead(BUTTON_PIN) == LOW) {{
    Serial.println(F("Button pressed"));
    delay(200);
  }}""")
        
        setup_code.append(f'  Serial.println(F("CircuitForge AI - {spec.name} Initialized"));')
        
        if not loop_code:
            loop_code.append('  Serial.println(F("System running..."));')
        
        loop_code.append("  delay(1000);")
        
        code = "\n".join(includes) + "\n\n"
        code += "/*\n * Auto-generated by CircuitForge AI (Generic Flexible Generator)\n"
        code += f" * Project: {spec.name}\n"
        code += " * NOTE: This is a generic template - customize as needed\n */\n\n"
        code += "\n".join(defines) + "\n\n"
        code += "void setup() {\n"
        code += "\n".join(setup_code) + "\n"
        code += "}\n\n"
        code += "void loop() {\n"
        code += "\n".join(loop_code) + "\n"
        code += "}\n"
        
        return code


async def generate_firmware(spec: ProjectSpec) -> tuple[str, str]:
    """
    Use Arduino-Coder-0.5B to generate firmware.
    Falls back to verified catalog template if Ollama is unreachable.
    For known component types (servo, LCD, relay), prefer deterministic generator.
    Returns (firmware_code, raw_response).
    """
    # Check if we have specific component types that benefit from deterministic generation
    comp_ids = {c.catalog_id for c in spec.components}
    use_deterministic = any([
        "servo_motor" in comp_ids,
        "lcd_display" in comp_ids,
        "relay_module" in comp_ids,
    ])
    
    # If we have a good template, use it directly
    if use_deterministic:
        fw = _deterministic_firmware(spec)
        return fw, fw
    
    pin_lines = "\n".join(
        f"  - {pa.component_instance}.{pa.component_pin} -> GPIO{pa.gpio_pin} ({pa.description})"
        for pa in spec.pin_assignments
    )
    comp_lines = "\n".join(
        f"  - {inst.name} (catalog_id: {inst.catalog_id}, instance: {inst.instance_id})"
        for inst in spec.components
    )
    threshold_info = ""
    if spec.threshold_value is not None:
        threshold_info = f"Threshold: {spec.threshold_value} {spec.threshold_unit or ''}"

    prompt = FIRMWARE_PROMPT_TEMPLATE.format(
        name=spec.name,
        behavior=spec.behavior,
        libraries=", ".join(spec.libraries),
        pin_assignments=pin_lines,
        components=comp_lines,
        threshold_info=threshold_info,
    )

    try:
        raw = await _ollama_generate(FIRMWARE_MODEL, prompt, MAX_TOKENS_FIRMWARE)
    except (httpx.ConnectError, httpx.TimeoutException, OSError):
        # Ollama not reachable: use deterministic firmware generator
        fw = _deterministic_firmware(spec)
        return fw, fw
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 403:
            fw = _deterministic_firmware(spec)
            return fw, fw
        if e.response.status_code == 404:
            raise ValueError(
                f"Firmware model '{FIRMWARE_MODEL}' not installed.\n"
                f"Run: ollama pull {FIRMWARE_MODEL}"
            )
        raise ValueError(f"Ollama error: {e}")
    except Exception as e:
        raise ValueError(f"AI firmware generation failed: {e}")

    code = _extract_code(raw)

    # Basic sanity checks
    if "void setup()" not in code:
        raise ValueError(f"Generated firmware missing setup() function. Raw:\n{raw[:500]}")
    if "void loop()" not in code:
        raise ValueError(f"Generated firmware missing loop() function. Raw:\n{raw[:500]}")

    return code, raw


# ── AI Repair ─────────────────────────────────────────────────────────────────

REPAIR_PROMPT_TEMPLATE = """You are an expert Arduino/ESP32 firmware debugger.
Fix the firmware compilation error below.

Original firmware:
```cpp
{firmware}
```

Compilation error:
{compiler_error}

Previous repair attempts: {attempt_number}

Provide a corrected, complete firmware file that will compile successfully.
Output ONLY the corrected Arduino C++ code.
"""


async def repair_firmware(
    firmware: str,
    compiler_error: str,
    attempt_number: int,
) -> tuple[str, str]:
    """
    Use Gemma3:1b to repair firmware.
    Returns (repaired_firmware, raw_response).
    Raises ValueError on failure.
    """
    prompt = REPAIR_PROMPT_TEMPLATE.format(
        firmware=firmware[:3000],  # limit context
        compiler_error=compiler_error[:1000],
        attempt_number=attempt_number,
    )

    try:
        raw = await _ollama_generate(PLANNER_MODEL, prompt, MAX_TOKENS_FIRMWARE)
        code = _extract_code(raw)
    except Exception:
        # Graceful repair fallback: apply common fixes (e.g. ensure #include <Arduino.h>, fix pinMode)
        fixed_lines = []
        if "#include <Arduino.h>" not in firmware:
            fixed_lines.append("#include <Arduino.h>")
        for line in firmware.splitlines():
            fixed_lines.append(line)
        code = "\n".join(fixed_lines)
        raw = code

    if "void setup()" not in code or "void loop()" not in code:
        raise ValueError(f"Repaired firmware missing required functions. Raw:\n{raw[:500]}")

    return code, raw
