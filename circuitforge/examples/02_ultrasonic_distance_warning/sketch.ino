/*
 * CircuitForge AI - Example 2: Ultrasonic Distance Warning System
 * Board: ESP32 DevKit V1
 * Sensor: HC-SR04 (TRIG: GPIO5, ECHO: GPIO18)
 * Actuator: Active Buzzer (GPIO19)
 * Alert Threshold: < 20 cm
 */

#include <Arduino.h>

#define TRIG_PIN 5
#define ECHO_PIN 18
#define BUZZER_PIN 19

const int DISTANCE_THRESHOLD_CM = 20;

void setup() {
  Serial.begin(115200);
  while (!Serial && millis() < 3000) { delay(10); }

  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);
  pinMode(BUZZER_PIN, OUTPUT);
  digitalWrite(BUZZER_PIN, LOW);

  Serial.println(F("================================================"));
  Serial.println(F("CircuitForge AI - Ultrasonic Distance Warning"));
  Serial.println(F("Alert distance: < 20 cm"));
  Serial.println(F("================================================"));
}

void loop() {
  // Clear the trigger pin
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);

  // Send 10us ultrasonic pulse
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);

  // Measure round-trip echo pulse duration in microseconds
  long duration = pulseIn(ECHO_PIN, HIGH, 30000); // 30ms timeout (approx 5 meters)

  if (duration == 0) {
    Serial.println(F("[WARN] Sensor out of range or echo timed out."));
    digitalWrite(BUZZER_PIN, LOW);
  } else {
    // Calculate distance in cm (speed of sound = 343 m/s = 0.0343 cm/us, divided by 2 for round-trip)
    float distanceCm = duration * 0.0343 / 2.0;

    Serial.print(F("Distance: "));
    Serial.print(distanceCm, 1);
    Serial.print(F(" cm  |  Buzzer: "));

    if (distanceCm < DISTANCE_THRESHOLD_CM) {
      digitalWrite(BUZZER_PIN, HIGH);
      Serial.println(F("ACTIVE (PROXIMITY ALERT!)"));
    } else {
      digitalWrite(BUZZER_PIN, LOW);
      Serial.println(F("OFF"));
    }
  }

  delay(200); // Sample rate: 5 Hz
}
