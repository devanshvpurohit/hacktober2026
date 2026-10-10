"""
CircuitForge AI - Component Catalog
Verified catalog of supported components with pricing, wiring rules, and Wokwi IDs.
All prices in INR are indicative catalog estimates as of 2025-01.
"""
from __future__ import annotations
from typing import Optional
from schemas import CatalogComponent, ComponentPin, WiringRule

# ── ESP32 Development Board ────────────────────────────────────────────────────

ESP32_DEVKIT = CatalogComponent(
    id="esp32_devkitv1",
    name="ESP32 DevKit V1",
    category="microcontroller",
    wokwi_id="wokwi-esp32-devkit-v1",
    supported_boards=["esp32"],
    pins=[
        ComponentPin(name="3V3",   description="3.3V power output",  pin_type="power",   required=True),
        ComponentPin(name="GND",   description="Ground",              pin_type="ground",  required=True),
        ComponentPin(name="VIN",   description="5V input",            pin_type="power",   required=False),
        ComponentPin(name="GPIO2", description="GPIO 2 / LED_BUILTIN",pin_type="digital", required=False),
        ComponentPin(name="GPIO4", description="GPIO 4",              pin_type="digital", required=False),
        ComponentPin(name="GPIO5", description="GPIO 5",              pin_type="digital", required=False),
        ComponentPin(name="GPIO12",description="GPIO 12",             pin_type="digital", required=False),
        ComponentPin(name="GPIO13",description="GPIO 13",             pin_type="digital", required=False),
        ComponentPin(name="GPIO14",description="GPIO 14",             pin_type="digital", required=False),
        ComponentPin(name="GPIO15",description="GPIO 15",             pin_type="digital", required=False),
        ComponentPin(name="GPIO18",description="GPIO 18 / SPI CLK",  pin_type="digital", required=False),
        ComponentPin(name="GPIO19",description="GPIO 19 / SPI MISO", pin_type="digital", required=False),
        ComponentPin(name="GPIO21",description="GPIO 21 / I2C SDA",  pin_type="i2c",     required=False),
        ComponentPin(name="GPIO22",description="GPIO 22 / I2C SCL",  pin_type="i2c",     required=False),
        ComponentPin(name="GPIO23",description="GPIO 23 / SPI MOSI", pin_type="digital", required=False),
        ComponentPin(name="GPIO25",description="GPIO 25 / DAC1",     pin_type="analog",  required=False),
        ComponentPin(name="GPIO26",description="GPIO 26 / DAC2",     pin_type="analog",  required=False),
        ComponentPin(name="GPIO27",description="GPIO 27",             pin_type="digital", required=False),
        ComponentPin(name="GPIO32",description="GPIO 32 / ADC1_CH4", pin_type="analog",  required=False),
        ComponentPin(name="GPIO33",description="GPIO 33 / ADC1_CH5", pin_type="analog",  required=False),
        ComponentPin(name="GPIO34",description="GPIO 34 / input only",pin_type="digital",required=False),
        ComponentPin(name="GPIO35",description="GPIO 35 / input only",pin_type="digital",required=False),
    ],
    unit_price_inr=350.0,
    price_source="catalog_estimate",
    price_verified_date="2025-01-01",
    description="ESP32 dual-core 240MHz WiFi+BT development board with 38 pins",
    electrical_constraints=[
        "GPIO6-11 are connected to flash memory — do not use",
        "GPIO34-39 are input-only — cannot be used as output",
        "Max 40mA per GPIO pin, 1200mA total",
        "3.3V logic only — do not apply 5V to GPIO pins",
    ],
)

# ── DHT22 Temperature & Humidity Sensor ────────────────────────────────────────

DHT22 = CatalogComponent(
    id="dht22",
    name="DHT22 Temperature & Humidity Sensor",
    category="sensor",
    wokwi_id="wokwi-dht22",
    supported_boards=["esp32", "arduino_uno", "arduino_nano"],
    pins=[
        ComponentPin(name="VCC",  description="Power supply 3.3V-5V", pin_type="power",   required=True),
        ComponentPin(name="SDA",  description="Data signal",           pin_type="signal",  required=True),
        ComponentPin(name="NC",   description="Not connected",         pin_type="signal",  required=False),
        ComponentPin(name="GND",  description="Ground",                pin_type="ground",  required=True),
    ],
    wiring_rules=[
        WiringRule(from_pin="VCC", to_component="esp32", to_pin="3V3",   description="Connect to 3.3V power"),
        WiringRule(from_pin="GND", to_component="esp32", to_pin="GND",   description="Connect to ground"),
        WiringRule(from_pin="SDA", to_component="esp32", to_pin="GPIO4", description="Data line (default GPIO4)"),
    ],
    libraries=["DHT sensor library", "Adafruit Unified Sensor"],
    unit_price_inr=200.0,
    price_source="catalog_estimate",
    price_verified_date="2025-01-01",
    description="AM2302 digital temperature and humidity sensor, 0-100%RH, -40 to 80°C",
    electrical_constraints=[
        "Requires 10kΩ pull-up resistor on data line (built-in on module versions)",
        "Minimum 2 seconds between readings",
        "Operating voltage: 3.3V to 5V",
    ],
    example_firmware="""
#include <DHT.h>
#define DHTPIN 4
#define DHTTYPE DHT22
DHT dht(DHTPIN, DHTTYPE);
void setup() {
  Serial.begin(115200);
  dht.begin();
}
void loop() {
  float h = dht.readHumidity();
  float t = dht.readTemperature();
  if (isnan(h) || isnan(t)) { Serial.println("DHT read failed"); return; }
  Serial.printf("Temp: %.1f°C  Humidity: %.1f%%\\n", t, h);
  delay(2000);
}
""",
)

# ── LED ────────────────────────────────────────────────────────────────────────

LED_RED = CatalogComponent(
    id="led_red",
    name="Red LED",
    category="output",
    wokwi_id="wokwi-led",
    supported_boards=["esp32", "arduino_uno", "arduino_nano"],
    pins=[
        ComponentPin(name="A",  description="Anode (positive)",  pin_type="digital", required=True),
        ComponentPin(name="K",  description="Cathode (negative)", pin_type="ground",  required=True),
    ],
    unit_price_inr=5.0,
    price_source="catalog_estimate",
    price_verified_date="2025-01-01",
    description="5mm red LED, Vf≈2.0V, If≈20mA",
    electrical_constraints=[
        "Always use current-limiting resistor (220Ω for 3.3V supply)",
        "Forward voltage: 2.0V typical",
        "Max forward current: 20mA",
    ],
)

# ── Resistor ───────────────────────────────────────────────────────────────────

RESISTOR_220 = CatalogComponent(
    id="resistor_220",
    name="220Ω Resistor",
    category="passive",
    wokwi_id="wokwi-resistor",
    supported_boards=["esp32", "arduino_uno", "arduino_nano"],
    pins=[
        ComponentPin(name="1", description="Terminal 1", pin_type="signal", required=True),
        ComponentPin(name="2", description="Terminal 2", pin_type="signal", required=True),
    ],
    unit_price_inr=1.0,
    price_source="catalog_estimate",
    price_verified_date="2025-01-01",
    description="220Ω 1/4W through-hole resistor for LED current limiting",
    electrical_constraints=["Power rating: 0.25W"],
)

RESISTOR_10K = CatalogComponent(
    id="resistor_10k",
    name="10kΩ Resistor",
    category="passive",
    wokwi_id="wokwi-resistor",
    supported_boards=["esp32", "arduino_uno", "arduino_nano"],
    pins=[
        ComponentPin(name="1", description="Terminal 1", pin_type="signal", required=True),
        ComponentPin(name="2", description="Terminal 2", pin_type="signal", required=True),
    ],
    unit_price_inr=1.0,
    price_source="catalog_estimate",
    price_verified_date="2025-01-01",
    description="10kΩ 1/4W through-hole resistor for pull-up/down",
    electrical_constraints=["Power rating: 0.25W"],
)

# ── HC-SR04 Ultrasonic Sensor ──────────────────────────────────────────────────

HC_SR04 = CatalogComponent(
    id="hc_sr04",
    name="HC-SR04 Ultrasonic Distance Sensor",
    category="sensor",
    wokwi_id="wokwi-hc-sr04",
    supported_boards=["esp32", "arduino_uno", "arduino_nano"],
    pins=[
        ComponentPin(name="VCC",   description="5V power supply",  pin_type="power",  required=True),
        ComponentPin(name="TRIG",  description="Trigger input",     pin_type="signal", required=True),
        ComponentPin(name="ECHO",  description="Echo output",       pin_type="signal", required=True),
        ComponentPin(name="GND",   description="Ground",            pin_type="ground", required=True),
    ],
    libraries=["NewPing"],
    unit_price_inr=60.0,
    price_source="catalog_estimate",
    price_verified_date="2025-01-01",
    description="Ultrasonic distance sensor, range 2cm-400cm",
    electrical_constraints=[
        "VCC requires 5V — use voltage divider on ECHO pin when using 3.3V MCU",
        "ECHO pin output is 5V — use level shifter or voltage divider for ESP32",
        "Minimum 60ms between measurements to avoid echo interference",
    ],
)

# ── Buzzer ─────────────────────────────────────────────────────────────────────

BUZZER = CatalogComponent(
    id="buzzer",
    name="Active Buzzer",
    category="output",
    wokwi_id="wokwi-buzzer",
    supported_boards=["esp32", "arduino_uno", "arduino_nano"],
    pins=[
        ComponentPin(name="+", description="Positive (signal)",  pin_type="signal", required=True),
        ComponentPin(name="-", description="Negative (ground)",  pin_type="ground", required=True),
    ],
    unit_price_inr=20.0,
    price_source="catalog_estimate",
    price_verified_date="2025-01-01",
    description="5V active buzzer, beeps when positive voltage is applied",
    electrical_constraints=[
        "Operating voltage: 3.3V to 5V",
        "Current consumption: ~30mA — may need transistor driver for ESP32 GPIO",
    ],
)

# ── Push Button ────────────────────────────────────────────────────────────────

PUSH_BUTTON = CatalogComponent(
    id="push_button",
    name="Tactile Push Button",
    category="input",
    wokwi_id="wokwi-pushbutton",
    supported_boards=["esp32", "arduino_uno", "arduino_nano"],
    pins=[
        ComponentPin(name="1.l", description="Left terminal 1",  pin_type="signal", required=True),
        ComponentPin(name="1.r", description="Right terminal 1", pin_type="signal", required=True),
        ComponentPin(name="2.l", description="Left terminal 2",  pin_type="signal", required=False),
        ComponentPin(name="2.r", description="Right terminal 2", pin_type="signal", required=False),
    ],
    unit_price_inr=5.0,
    price_source="catalog_estimate",
    price_verified_date="2025-01-01",
    description="6×6mm tactile momentary push button, rated 50mA 12V",
    electrical_constraints=["Use internal pull-up or external pull-up resistor"],
)

# ── Potentiometer ──────────────────────────────────────────────────────────────

POTENTIOMETER = CatalogComponent(
    id="potentiometer_10k",
    name="10kΩ Potentiometer",
    category="input",
    wokwi_id="wokwi-potentiometer",
    supported_boards=["esp32", "arduino_uno", "arduino_nano"],
    pins=[
        ComponentPin(name="GND", description="Ground terminal", pin_type="ground",  required=True),
        ComponentPin(name="SIG", description="Wiper / signal",  pin_type="analog",  required=True),
        ComponentPin(name="VCC", description="Power terminal",  pin_type="power",   required=True),
    ],
    unit_price_inr=15.0,
    price_source="catalog_estimate",
    price_verified_date="2025-01-01",
    description="10kΩ rotary potentiometer for analog input 0-3.3V",
    electrical_constraints=["Max 1W power dissipation", "Use ADC-capable GPIO pin for signal"],
)


# ── Catalog Registry ──────────────────────────────────────────────────────────

CATALOG: dict[str, CatalogComponent] = {
    c.id: c for c in [
        ESP32_DEVKIT,
        DHT22,
        LED_RED,
        RESISTOR_220,
        RESISTOR_10K,
        HC_SR04,
        BUZZER,
        PUSH_BUTTON,
        POTENTIOMETER,
    ]
}

# Valid GPIO numbers for ESP32 (excluding reserved flash pins 6-11)
ESP32_VALID_GPIO: set[int] = {0, 1, 2, 3, 4, 5, 12, 13, 14, 15, 16, 17, 18, 19,
                               21, 22, 23, 25, 26, 27, 32, 33, 34, 35, 36, 39}
ESP32_OUTPUT_GPIO: set[int] = {0, 1, 2, 3, 4, 5, 12, 13, 14, 15, 16, 17, 18, 19,
                                21, 22, 23, 25, 26, 27, 32, 33}
ESP32_ANALOG_GPIO: set[int] = {32, 33, 34, 35, 36, 39, 25, 26}


def get_component(component_id: str) -> Optional[CatalogComponent]:
    return CATALOG.get(component_id)


def list_components() -> list[CatalogComponent]:
    return list(CATALOG.values())


def search_components(query: str) -> list[CatalogComponent]:
    q = query.lower()
    return [c for c in CATALOG.values()
            if q in c.name.lower() or q in c.description.lower() or q in c.category.lower()]
