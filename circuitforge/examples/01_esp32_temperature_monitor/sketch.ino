/*
 * CircuitForge AI - Example 1: ESP32 Temperature Monitor
 * Board: ESP32 DevKit V1
 * Sensors: DHT22 (GPIO4)
 * Actuator: Red LED (GPIO2) with 220 Ohm current-limiting resistor
 * Threshold: 30.0 degrees Celsius
 */

#include <Arduino.h>
#include <DHT.h>

#define DHTPIN 4
#define DHTTYPE DHT22
#define LED_PIN 2

const float TEMP_THRESHOLD = 30.0;
DHT dht(DHTPIN, DHTTYPE);

void setup() {
  Serial.begin(115200);
  while (!Serial && millis() < 3000) { delay(10); }
  
  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, LOW);
  
  dht.begin();
  Serial.println(F("========================================"));
  Serial.println(F("CircuitForge AI - ESP32 Temp Monitor"));
  Serial.println(F("Threshold: 30.0 C"));
  Serial.println(F("========================================"));
}

void loop() {
  delay(2000); // DHT22 requires at least 2s between samplings

  float humidity = dht.readHumidity();
  float temperature = dht.readTemperature();

  if (isnan(humidity) || isnan(temperature)) {
    Serial.println(F("[ERROR] Failed to read from DHT22 sensor! Check wiring."));
    return;
  }

  Serial.print(F("Temp: "));
  Serial.print(temperature, 1);
  Serial.print(F(" °C  |  Humidity: "));
  Serial.print(humidity, 1);
  Serial.print(F(" %  |  LED Status: "));

  if (temperature > TEMP_THRESHOLD) {
    digitalWrite(LED_PIN, HIGH);
    Serial.println(F("ON (HIGH TEMP ALERT)"));
  } else {
    digitalWrite(LED_PIN, LOW);
    Serial.println(F("OFF (NORMAL)"));
  }
}
