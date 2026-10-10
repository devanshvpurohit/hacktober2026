# Wokwi Simulation Guide
### CircuitForge AI Integration

CircuitForge AI exports Wokwi-compatible circuit diagrams and firmware so you can simulate ESP32 designs without physical hardware.

---

## 1. Wokwi Architecture

CircuitForge AI generates the standard Wokwi project bundle:
1. `diagram.json`: Declarative circuit layout specifying components, coordinates, attributes, and netlist wire connections.
2. `sketch.ino`: Arduino C++ code matching the exact pin assignments in `diagram.json`.
3. `libraries.txt`: Pinned list of Arduino libraries required by the sketch.
4. `wokwi.toml`: Simulator configuration defining binary target paths and architecture.

---

## 2. Modes of Simulation

### Mode A: Manual Browser Simulation (Always Available)
You do not need any API key, CLI installation, or local binary to simulate:
1. Generate your project in CircuitForge AI.
2. Navigate to [https://wokwi.com](https://wokwi.com).
3. Select **ESP32** -> **ESP32 DevKit v1**.
4. Switch to the `diagram.json` tab in Wokwi and replace its contents with the code from CircuitForge AI's **Circuit Diagram** tab.
5. In `sketch.ino`, replace the editor content with the generated firmware from CircuitForge AI.
6. Click the green **Play** button to begin simulation.
7. You can interactively manipulate sensor controls (e.g. adjust temperature sliders on the DHT22 or distance sliders on the HC-SR04) and view real-time Serial output.

### Mode B: Automated Simulation (Wokwi CLI)
When `wokwi-cli` is installed locally:
1. Set your Wokwi CI token if required:
   ```bash
   export WOKWI_CLI_TOKEN="your-token"
   ```
2. CircuitForge AI provides a **Run Simulation** button directly inside the web dashboard.
3. The backend executes `wokwi-cli run .` in the project workspace and captures exit status, timeout watchdog, and terminal logs.
