# What CircuitForge AI Does

CircuitForge AI is a **local-first, privacy-focused web application** that converts natural-language IoT ideas into validated circuit diagrams, compilable Arduino firmware, Wokwi-compatible simulations, AI-assisted repairs, and itemized bills of materials.

## Core Capabilities

- **100% Local Inference & Storage**: All AI processing runs via Ollama on your machine. No cloud APIs, no data leaves your device.
- **Natural Language to Circuit**: Input an IoT idea in plain English, get a standards-compliant circuit diagram (`diagram.json`) for Wokwi.
- **Arduino Firmware Generation**: Generated firmware compiles directly via `arduino-cli` for real hardware.
- **Wokwi Simulation**: Dual-mode — automated CLI simulation when `wokwi-cli` is installed, or manual browser import at <https://wokwi.com>.
- **Bill of Materials (BOM)**: Price estimates in INR using Python `Decimal` arithmetic for accurate cost calculation.
- **AI-Assisted Repair**: Up to 3 bounded repair attempts using `gemma3:1b` with validation checkpoints.
- **ZIP Export**: Standalone project bundles with path-traversal prevention.

## Verified Hardware Catalog

Predefined components with Wokwi part IDs and INR pricing:
- ESP32 DevKit V1, DHT22 sensor, HC-SR04 ultrasonic sensor, LEDs, resistors, buzzer, push button, potentiometer

## Technology Stack

- **Frontend**: React 18, TypeScript, Vite, Tailwind CSS
- **Backend**: Python 3.11+, FastAPI, Pydantic v2, aiosqlite
- **AI Models (local Ollama)**: `gemma3:1b` (planner/repair), `hf.co/tapariapurv/Arduino-Coder-0.5B-GGUF-v1:Q4_K_M` (firmware generator)
- **Toolchain**: Arduino CLI v1.5+, Wokwi CLI & Online Editor

## Quick Start

1. Install Arduino CLI: `brew install arduino-cli`
2. Install and launch Ollama: `brew install ollama && ollama serve`
3. Pull models: `ollama pull gemma3:1b` and `ollama pull hf.co/tapariapurv/Arduino-Coder-0.5B-GGUF-v1:Q4_K_M`
4. Install ESP32 board core: `arduino-cli core update-index && arduino-cli core install esp32:esp32`
5. Run: `./start.sh`
6. Open browser at <http://127.0.0.1:8000>