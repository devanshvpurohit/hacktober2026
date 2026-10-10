# Example 1: ESP32 Temperature Monitor with DHT22 and LED

## Objective
Monitor ambient temperature using a digital DHT22 sensor and illuminate a red status LED when temperature exceeds 30.0°C.

## Hardware Components & Indicative Pricing (INR)
- **ESP32 DevKit V1**: ₹350.00
- **DHT22 Temperature & Humidity Sensor**: ₹200.00
- **Red 5mm LED**: ₹5.00
- **220Ω Resistor**: ₹1.00
- **Total Estimated BOM**: ₹556.00

## Pin Configuration
| Component | Pin | ESP32 GPIO | Description |
|-----------|-----|------------|-------------|
| DHT22 | VCC | 3V3 | Power (3.3V) |
| DHT22 | GND | GND | Ground |
| DHT22 | SDA | GPIO4 | Digital Data Signal |
| Red LED | Anode (+) | GPIO2 | Output signal (active HIGH) |
| Red LED | Cathode (-) | Via 220Ω to GND | Current limiting to ground |

## Simulation Steps
### Option A: Local / CLI
```bash
wokwi-cli run .
```

### Option B: Wokwi Online (Manual)
1. Open [https://wokwi.com](https://wokwi.com).
2. Create a new ESP32 project.
3. Paste `sketch.ino` into the code editor.
4. Paste `diagram.json` into the `diagram.json` tab.
5. Click Play to start the simulation. You can adjust the DHT22 temperature slider in the simulator to test threshold triggering.
