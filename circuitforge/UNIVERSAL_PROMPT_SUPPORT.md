# Universal Prompt Support - Implementation Plan

## Goal
Make CircuitForge accept **ANY** type of prompt and intelligently generate appropriate IoT projects.

## Current State
✅ Works for: servo, LCD, relay, temperature, distance
❌ Needs improvement: Generic prompts, complex multi-component requests

## Enhanced Smart Planner

### Key Features
1. **Component Extraction** - Parse request for component keywords
2. **Dynamic GPIO Allocation** - Automatically assign pins based on components
3. **Intelligent Combination** - Mix components based on request
4. **Behavior Generation** - Create meaningful descriptions from components

### Supported Keywords

#### Actuators
- `servo`, `motor`, `rotate` → Servo Motor
- `relay`, `switch` (with lamp/appliance) → Relay Module

#### Sensors
- `temperature`, `temp`, `humidity`, `dht` → DHT22 Sensor
- `distance`, `ultrasonic`, `sr04`, `proximity` → HC-SR04
- `potentiometer`, `pot`, `knob`, `analog` → Potentiometer

#### Displays
- `lcd`, `display`, `oled`, `screen` → LCD/OLED Display

#### Input/Output
- `button`, `press`, `input` → Push Button
- `led`, `light`, `indicator` → LED
- `buzzer`, `alarm`, `alert`, `sound`, `beep` → Buzzer

### Example Transformations

| User Input | Components Generated |
|-----------|---------------------|
| "servo motor with button" | Servo + Button + LED |
| "oled display with temperature" | OLED + DHT22 |
| "distance sensor with buzzer" | HC-SR04 + Buzzer + LED |
| "relay lamp control" | Relay + Button + LED |
| "smart plant monitor" | DHT22 + LED + Buzzer |
| "door sensor" | Button + LED + Buzzer |
| "temperature display" | DHT22 + LCD + LED |

### Implementation Strategy

```python
def smart_plan(user_request):
    # 1. Extract keywords
    components = extract_components(user_request)
    
    # 2. Allocate GPIOs dynamically
    pins = allocate_gpio_pins(components)
    
    # 3. Generate behavior description
    behavior = generate_behavior(components)
    
    # 4. Select required libraries
    libraries = select_libraries(components)
    
    # 5. Create project spec
    return ProjectSpec(components, pins, behavior, libraries)
```

## Benefits

✅ Works with **any prompt**
✅ Combines multiple components intelligently
✅ No hard-coded templates
✅ Automatic GPIO management
✅ Smart behavior generation
✅ Flexible and extensible

## Next Steps

1. ✅ Implement smart component extraction
2. ✅ Add dynamic GPIO allocation
3. ✅ Generate behavior from components
4. ⏳ Test with various prompts
5. ⏳ Add more component types
6. ⏳ Improve firmware generation to match

## Testing Prompts

Try these to verify universal support:
- "build a servo motor that moves with a button"
- "oled display showing temperature and humidity"
- "distance sensor with buzzer alarm"
- "relay to control a lamp with button"
- "smart garden monitor with alerts"
- "door sensor system"
- "temperature logger with display"
- "motion detector with led"
- "water level indicator"
- "automatic fan controller"

---

**Status:** Ready for implementation
**Impact:** Makes CircuitForge truly universal!
