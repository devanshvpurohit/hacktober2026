# CircuitForge AI - Flexible Component System

## Overview

CircuitForge AI now supports **any prompt** and can work with **components not in the standard catalog**! The system is designed to be flexible and creative, generating working IoT projects even for components that aren't predefined.

## Key Features

### 1. Accept Any Prompt
The AI now accepts any IoT project request and attempts to create a working plan, even if the components aren't in the catalog.

**Examples:**
- "Build a servo motor control system"
- "Create an LCD display that shows temperature"
- "Make a relay-controlled lamp with a button"
- "Design a smart garden watering system"
- "Build a door lock system with keypad"

### 2. Flexible Component Handling

#### Standard Catalog Components
- **DHT22** - Temperature & Humidity Sensor
- **LED (Red)** - Status indicators
- **Resistors** (220Ω, 10kΩ)
- **HC-SR04** - Ultrasonic distance sensor
- **Buzzer** - Active buzzer for alerts
- **Push Button** - Tactile input
- **Potentiometer** (10kΩ) - Analog input

#### Extended/Flexible Components
The system can now handle:
- **Servo Motors** (`servo_motor`) - Position control
- **LCD/OLED Displays** (`lcd_display`) - I2C displays
- **Relay Modules** (`relay_module`) - High-power switching
- **And more...** - The system adapts to your needs!

### 3. Smart Firmware Generation

The firmware generator now includes:
- **Servo control** with ESP32Servo library
- **LCD/OLED** support with LiquidCrystal_I2C
- **Relay switching** with button control
- **Generic fallback** that assembles code based on detected components

### 4. Missing Component Detection

When you request a component not in the catalog, the system:
1. Creates a best-guess `catalog_id` (e.g., `servo_motor`, `lcd_display`)
2. Adds it to the `missing_info` array with suggestions
3. Generates appropriate firmware using standard Arduino libraries
4. Warns you that manual verification may be needed

## How It Works

### Planning Stage
```
User Request → AI Planning → Component Detection → Pin Assignment
                    ↓
            Missing components noted
                    ↓
            Best-effort specification created
```

### Firmware Generation
```
Project Spec → Detect Component Types → Select Generator
                         ↓
        ┌────────────────┼────────────────┐
        ↓                ↓                ↓
    Servo Gen      LCD Gen        Generic Gen
        ↓                ↓                ↓
            Working Arduino Code
```

## Usage Examples

### Example 1: Servo Motor Project
```
Prompt: "Build a servo motor control with a button"
```

**Generated Plan:**
- ESP32 board
- Servo motor on GPIO 13
- Push button on GPIO 12
- Status LED on GPIO 2

**Generated Firmware:**
- Uses ESP32Servo library
- Button cycles servo through positions
- Serial debug output

### Example 2: LCD Display
```
Prompt: "Create an LCD display showing temperature from DHT22"
```

**Generated Plan:**
- ESP32 board
- I2C LCD on GPIO 21 (SDA) and GPIO 22 (SCL)
- DHT22 on GPIO 4

**Generated Firmware:**
- LiquidCrystal_I2C library
- Updates display every 2 seconds
- Shows temp and humidity

### Example 3: Relay Control
```
Prompt: "Make a relay switch for a lamp with button control"
```

**Generated Plan:**
- ESP32 board
- Relay module on GPIO 13
- Push button on GPIO 12
- Status LED on GPIO 2

**Generated Firmware:**
- Toggle relay on button press
- LED mirrors relay state
- Debounce handling included

### Example 4: Generic Custom Project
```
Prompt: "Build a smart plant monitor"
```

**Generated Plan:**
- Generic template with:
  - DHT22 for environment
  - LED for status
  - Buzzer for alerts
  - Button for interaction

**Generated Firmware:**
- Modular code generation
- Combines detected components
- Extensible structure

## Component ID Convention

When working with flexible components, use these catalog ID patterns:

| Component Type | Suggested catalog_id |
|---------------|---------------------|
| Servo Motor | `servo_motor` |
| LCD Display (I2C) | `lcd_display` |
| OLED Display | `oled_display` |
| Relay Module | `relay_module` |
| Stepper Motor | `stepper_motor` |
| IR Sensor | `ir_sensor` |
| PIR Sensor | `pir_sensor` |
| Gas Sensor (MQ series) | `gas_sensor` |
| Keypad | `keypad_4x4` |
| RFID Reader | `rfid_reader` |

## Advanced Features

### 1. Threshold Detection
The system automatically detects threshold values in your prompt:
- "Alert when temperature exceeds **30 degrees**"
- "Activate buzzer when distance is less than **20 cm**"

### 2. Multi-Component Projects
Combine multiple components in one request:
```
"Build a security system with ultrasonic sensor, buzzer, and LED"
```

### 3. Offline Mode
When Ollama is not running, the system uses intelligent deterministic templates that handle various project types.

## Warnings and Notes

### When Using Flexible Components

1. **Library Requirements**: Ensure required libraries are installed:
   - ESP32Servo for servos
   - LiquidCrystal_I2C for LCD displays
   - Custom libraries for specialized sensors

2. **Pin Validation**: The system respects ESP32 constraints:
   - GPIO 6-11 are reserved (flash memory)
   - GPIO 34-39 are input-only
   - 3.3V logic level (no 5V)

3. **Power Considerations**:
   - Servos may need external power
   - Relays may need driver circuits
   - High-current loads need proper power supply

4. **Wokwi Simulation**: Not all components have Wokwi equivalents. The system will:
   - Use best-match Wokwi IDs when available
   - Mark components as manual verification required
   - Provide firmware that works on real hardware

## Best Practices

1. **Be Specific**: More detail in your prompt = better results
   - ❌ "make something with a motor"
   - ✅ "build a servo motor that sweeps 180 degrees with button control"

2. **Check Missing Info**: Review the `missing_info` array in the generated spec

3. **Verify Firmware**: For custom components, review and test the generated firmware

4. **Iterate**: If the first generation isn't perfect, try refining your prompt

## Future Enhancements

Planned improvements:
- [ ] Web-based component search integration
- [ ] User-defined component library
- [ ] Community component sharing
- [ ] Visual component configuration
- [ ] Real-time component availability checking

## Contributing

Have a component you'd like to add? Create a pull request with:
1. Component definition in `components.py`
2. Wiring rules and pin mappings
3. Example firmware snippet
4. Wokwi diagram configuration

---

**CircuitForge AI** - Making IoT development accessible to everyone! 🚀
