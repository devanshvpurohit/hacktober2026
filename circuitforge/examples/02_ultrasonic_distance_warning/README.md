# Example 2: Ultrasonic Distance Warning System

## Objective
Measure distance using an HC-SR04 ultrasonic sensor and trigger an active buzzer when an obstacle approaches closer than 20 cm.

## Hardware Components & Indicative Pricing (INR)
- **ESP32 DevKit V1**: ₹350.00
- **HC-SR04 Ultrasonic Distance Sensor**: ₹60.00
- **Active Buzzer (5V)**: ₹20.00
- **Total Estimated BOM**: ₹430.00

## Pin Configuration
| Component | Pin | ESP32 GPIO | Description |
|-----------|-----|------------|-------------|
| HC-SR04 | VCC | VIN (5V) | Power supply |
| HC-SR04 | GND | GND | Ground |
| HC-SR04 | TRIG | GPIO5 | Output pulse (10us trigger) |
| HC-SR04 | ECHO | GPIO18 | Input pulse measurement |
| Buzzer | Positive (+) | GPIO19 | High active buzzer drive |
| Buzzer | Negative (-) | GND | Ground return |

## Simulation Steps
### Local / CLI
```bash
wokwi-cli run .
```

### Wokwi Online (Manual)
1. Open [https://wokwi.com](https://wokwi.com).
2. Create an ESP32 project.
3. Paste `sketch.ino` into the code editor.
4. Paste `diagram.json` into the `diagram.json` tab.
5. Click Play. Drag the distance slider on the HC-SR04 to hear the buzzer tone trigger below 20 cm.
