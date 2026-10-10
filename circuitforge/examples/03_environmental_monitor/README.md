# Example 3: Multi-Sensor Environmental Monitor with Dynamic Threshold

## Objective
Continuous environmental monitoring using a DHT22 sensor, an analog potentiometer to dynamically adjust the temperature alarm setpoint in real time, and audiovisual indicators (LED and Buzzer).

## Hardware Components & Indicative Pricing (INR)
- **ESP32 DevKit V1**: ₹350.00
- **DHT22 Temperature & Humidity Sensor**: ₹200.00
- **10kΩ Rotary Potentiometer**: ₹15.00
- **Red 5mm LED**: ₹5.00
- **220Ω Resistor**: ₹1.00
- **Active Buzzer (5V)**: ₹20.00
- **Total Estimated BOM**: ₹591.00

## Pin Configuration
| Component | Pin | ESP32 GPIO | Description |
|-----------|-----|------------|-------------|
| DHT22 | SDA | GPIO4 | Digital data signal |
| DHT22 | VCC / GND | 3V3 / GND | Power supply |
| Potentiometer | SIG (wiper) | GPIO34 | ADC1 input (voltage 0 - 3.3V) |
| Potentiometer | VCC / GND | 3V3 / GND | Voltage reference rail |
| Red LED | Anode (+) | GPIO2 | Active HIGH alarm indicator |
| Red LED | Cathode (-) | Via 220Ω to GND | Current limiting to ground |
| Buzzer | Positive (+) | GPIO19 | Active HIGH audio alarm |
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
5. Click Play. Turn the potentiometer dial to adjust the threshold in real time, and adjust the DHT22 temperature to observe LED and buzzer alarms.
