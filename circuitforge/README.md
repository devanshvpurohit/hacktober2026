# CircuitForge AI
### Local-First AI-Powered IoT Builder with Arduino, ESP32, and Wokwi

CircuitForge AI is a functional, local-first web application that converts natural-language IoT ideas into validated circuit diagrams, compilable Arduino firmware, Wokwi-compatible simulations, AI-assisted repairs, and itemized bills of materials with indicative pricing in INR.

---

## 1. Key Highlights & Local Privacy Boundaries

- **100% Local Inference & Storage**: Uses local models via Ollama. No cloud AI APIs, no remote LLM fallbacks, no data leaves your machine.
- **Hardware-Constrained Planning**: Natural language requirements are mapped strictly to a verified local component catalog with electrical constraint validation.
- **Deterministic Circuit Generation**: Produces standards-compliant `diagram.json` for Wokwi using proven templates rather than hallucinated JSON.
- **Real Arduino CLI Compilation**: Compiles generated Arduino C++ firmware directly with `arduino-cli`.
- **Wokwi Integration**: Dual-mode simulation supporting both automated local CLI simulation (when installed) and zero-setup manual import at [wokwi.com](https://wokwi.com).
- **Bounded AI-Assisted Repair**: Up to 3 bounded repair attempts using `gemma3:1b` with validation checkpoints.
- **Bill of Materials (INR)**: Accurate monetary calculation using Python `Decimal` arithmetic with catalog-verified price estimates.
- **Complete ZIP Export**: Exports standalone project bundles with path-traversal prevention.

---

## 2. Technology Stack

- **Frontend**:
  - React 18 / TypeScript / Vite / Tailwind CSS engineering dashboard
  - Embedded responsive web interface with visual SVG circuit rendering
  - Dark theme with cyan accents
- **Backend**:
  - Python 3.11+ / FastAPI / Pydantic v2 / aiosqlite
  - Asynchronous safe subprocess management with output size limits
- **AI Models (Local Ollama)**:
  - Planner & Repair: `gemma3:1b`
  - Firmware Generator: `hf.co/tapariapurv/Arduino-Coder-0.5B-GGUF-v1:Q4_K_M`
- **Embedded Toolchain**:
  - Arduino CLI v1.5+
  - Wokwi CLI & Wokwi Online Editor

---

## 3. Verified Hardware Component Catalog

| Identifier | Name | Category | Wokwi Part ID | Price (INR) |
|------------|------|----------|---------------|-------------|
| `esp32_devkitv1` | ESP32 DevKit V1 (38-pin) | Microcontroller | `wokwi-esp32-devkit-v1` | ₹350.00 |
| `dht22` | DHT22 Temp & Humidity Sensor | Sensor | `wokwi-dht22` | ₹200.00 |
| `hc_sr04` | HC-SR04 Ultrasonic Distance Sensor | Sensor | `wokwi-hc-sr04` | ₹60.00 |
| `led_red` | 5mm Red LED | Output | `wokwi-led` | ₹5.00 |
| `resistor_220` | 220Ω 1/4W Resistor | Passive | `wokwi-resistor` | ₹1.00 |
| `resistor_10k` | 10kΩ 1/4W Resistor | Passive | `wokwi-resistor` | ₹1.00 |
| `buzzer` | 5V Active Buzzer | Output | `wokwi-buzzer` | ₹20.00 |
| `push_button` | 6x6mm Tactile Push Button | Input | `wokwi-pushbutton` | ₹5.00 |
| `potentiometer_10k` | 10kΩ Rotary Potentiometer | Input | `wokwi-potentiometer` | ₹15.00 |

---

## 4. Built-in Example Projects

1. **`01_esp32_temperature_monitor` (MVP Acceptance)**:
   - ESP32 + DHT22 (GPIO4) + Red LED (GPIO2) with 220Ω resistor.
   - Activates LED when temperature exceeds 30.0°C.
   - Total BOM: ₹556.00 INR.
2. **`02_ultrasonic_distance_warning`**:
   - ESP32 + HC-SR04 (TRIG: GPIO5, ECHO: GPIO18) + Active Buzzer (GPIO19).
   - Triggers buzzer when obstacle distance < 20 cm.
   - Total BOM: ₹430.00 INR.
3. **`03_environmental_monitor`**:
   - ESP32 + DHT22 (GPIO4) + 10kΩ Potentiometer (GPIO34) + Red LED (GPIO2) + Buzzer (GPIO19).
   - Dynamically adjusts temperature threshold using analog potentiometer dial.
   - Total BOM: ₹591.00 INR.

---

## 5. Quick Start (macOS Apple Silicon)

### Prerequisites

```bash
# 1. Install Arduino CLI
brew install arduino-cli

# 2. Install and launch Ollama (for live local LLMs)
brew install ollama
ollama serve

# 3. Pull required local models
ollama pull gemma3:1b
ollama pull hf.co/tapariapurv/Arduino-Coder-0.5B-GGUF-v1:Q4_K_M

# 4. Install ESP32 board core (for firmware compilation)
arduino-cli core update-index
arduino-cli core install esp32:esp32
```

### Running CircuitForge AI

Execute the one-command startup script:

```bash
./start.sh
```

Then open your browser at:
- **Web Dashboard**: [http://127.0.0.1:8000](http://127.0.0.1:8000)
- **API Documentation**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

---

## 6. Verification and Automated Testing

Run the full automated test suite (unit tests, example tests, and end-to-end API lifecycle):

```bash
# Unit Tests (24 checks: catalog, validators, BOM math, diagram syntax, ZIP safety)
python3 tests/unit/test_core.py

# Example Projects Integration Tests (structure, pin consistency, diagram format)
python3 tests/integration/test_examples.py

# End-to-End API Integration Tests (lifecycle: create -> plan -> generate -> validate -> BOM -> export)
python3 tests/integration/test_e2e_api.py
```

All 3 test suites pass with 0 errors.

---

## 7. Wokwi Simulation Workflow

### Mode A: Automated CLI Simulation
When `wokwi-cli` is present and authenticated:
Click **Run Simulation** in the workspace. CircuitForge AI invokes `wokwi-cli run .` and renders stdout/stderr in the web console.

### Mode B: Manual Web Simulation (Always Ready)
1. In the project workspace, navigate to the **Wokwi Simulation** tab or copy from the **Firmware** and **Circuit Diagram** tabs.
2. Open [https://wokwi.com](https://wokwi.com) and create an ESP32 project.
3. Paste `sketch.ino` into the code editor and `diagram.json` into the diagram tab.
4. Click the green Play button to simulate interactively!

---

## 8. Repository Layout

```
circuitforge/
├── apps/
│   ├── backend/
│   │   ├── ai/               # Ollama LLM integration (gemma3:1b & Arduino-Coder)
│   │   ├── catalog/          # Verified hardware definitions, BOM & diagram generator
│   │   ├── simulator/        # Arduino CLI compiler & Wokwi runners
│   │   ├── storage/          # SQLite database and artifact manager
│   │   ├── validators/       # Hardware, pin collision, diagram & ZIP validators
│   │   ├── static/           # Self-contained dark-theme engineering dashboard
│   │   ├── main.py           # FastAPI application
│   │   ├── schemas.py        # Central Pydantic models
│   │   └── system_check.py   # Truthful tool & environment detector
│   └── frontend/             # React 18 / TypeScript / Vite source code
├── examples/                 # 3 verified reference IoT projects
├── tests/
│   ├── unit/                 # Validator, catalog, BOM, diagram, ZIP tests
│   └── integration/          # Example validation and full E2E API tests
├── workspace/                # Local SQLite database and project folders
├── docs/                     # Detailed installation and simulation guides
└── start.sh                  # One-command development runner
```
