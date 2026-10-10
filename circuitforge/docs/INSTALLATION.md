# Installation and Toolchain Guide
### CircuitForge AI on macOS (Apple Silicon M1/M2/M3/M4)

This guide walks you through setting up all components of CircuitForge AI locally.

---

## 1. System Requirements

- **Operating System**: macOS 13+ (Ventura, Sonoma, Sequoia)
- **Architecture**: Apple Silicon (`arm64`)
- **Memory**: Minimum 8GB RAM (16GB recommended for running Ollama models smoothly)
- **Disk Space**: ~5GB free disk space for toolchains and local models

---

## 2. Step-by-Step Toolchain Setup

### Step A: Python 3.11+
Verify Python version:
```bash
python3 --version
```
Install backend dependencies:
```bash
cd apps/backend
pip3 install -r requirements.txt
```

### Step B: Local AI Engine (Ollama)
Ollama runs LLMs locally with Metal acceleration on Apple Silicon GPUs.

1. Install via Homebrew:
   ```bash
   brew install ollama
   ```
2. Start the Ollama background daemon:
   ```bash
   ollama serve
   ```
3. Pull the exact configured model roles:
   - **Planner & Repair Model**:
     ```bash
     ollama pull gemma3:1b
     ```
   - **Arduino C++ Firmware Generator**:
     ```bash
     ollama pull hf.co/tapariapurv/Arduino-Coder-0.5B-GGUF-v1:Q4_K_M
     ```
4. Verify inference test:
   ```bash
   ollama run gemma3:1b "Say OK"
   ```

### Step C: Arduino CLI
Used to compile C++ sketches into ESP32 binaries.

1. Install via Homebrew:
   ```bash
   brew install arduino-cli
   ```
2. Update package index:
   ```bash
   arduino-cli core update-index
   ```
3. Install ESP32 board core:
   ```bash
   arduino-cli core install esp32:esp32
   ```
4. Verify installation:
   ```bash
   arduino-cli core list
   # Expected output shows: esp32:esp32 ...
   ```
5. Install required Arduino libraries:
   ```bash
   arduino-cli lib install "DHT sensor library"
   arduino-cli lib install "Adafruit Unified Sensor"
   ```

### Step D: Wokwi Simulation (Optional for Automation)
Automated simulation requires `wokwi-cli`. If not installed, CircuitForge AI seamlessly guides you through manual simulation on [wokwi.com](https://wokwi.com).

To install `wokwi-cli`:
```bash
curl -L https://wokwi.com/ci/install.sh | sh
```

---

## 3. Starting CircuitForge AI

From the `circuitforge` root directory:
```bash
./start.sh
```

The server binds to `127.0.0.1:8000`. Navigate to [http://127.0.0.1:8000](http://127.0.0.1:8000) to begin building!
