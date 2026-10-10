/*
 * CircuitForge AI - Example 3: Environmental Monitor with Dynamic Threshold
 * Board: ESP32 DevKit V1
 * Sensor: DHT22 (GPIO4)
 * Input: 10k Potentiometer (GPIO34 - Analog ADC1)
 * Actuators: Red LED (GPIO2), Active Buzzer (GPIO19)
 * Description: Reads temperature & humidity; potentiometer dynamically sets
 * the alert temperature threshold between 20.0°C and 45.0°C.
 */

#include <Arduino.h>
#include <DHT.h>

#define DHTPIN 4
#define DHTTYPE DHT22
#define POT_PIN 34       // ADC1 channel 6 - input only
#define LED_PIN 2
#define BUZZER_PIN 19

DHT dht(DHTPIN, DHTTYPE);

void setup() {
  Serial.begin(115200);
  while (!Serial && millis() < 3000) { delay(10); }

  pinMode(LED_PIN, OUTPUT);
  pinMode(BUZZER_PIN, OUTPUT);
  pinMode(POT_PIN, INPUT);

  digitalWrite(LED_PIN, LOW);
  digitalWrite(BUZZER_PIN, LOW);

  dht.begin();
  Serial.println(F("=================================================="));
  Serial.println(F("CircuitForge AI - Dynamic Environmental Monitor"));
  Serial.println(F("Potentiometer adjusts alert threshold (20C - 45C)"));
  Serial.println(F("=================================================="));
}

void loop() {
  delay(2000); // Sensor read interval

  // Read analog value from potentiometer (0 - 4095 on ESP32 12-bit ADC)
  int potRaw = analogRead(POT_PIN);
  // Map ADC range to temperature threshold: 20.0 C to 45.0 C
  float thresholdTemp = 20.0 + (potRaw / 4095.0) * 25.0;

  float humidity = dht.readHumidity();
  float temperature = dht.readTemperature();

  if (isnan(humidity) || isnan(temperature)) {
    Serial.println(F("[ERROR] Failed to read DHT22!"));
    return;
  }

  Serial.print(F("Temp: "));
  Serial.print(temperature, 1);
  Serial.print(F(" °C  |  Humidity: "));
  Serial.print(humidity, 1);
  Serial.print(F(" %  |  Threshold: "));
  Serial.print(thresholdTemp, 1);
  Serial.print(F(" °C  |  Status: "));

  if (temperature > thresholdTemp) {
    digitalWrite(LED_PIN, HIGH);
    digitalWrite(BUZZER_PIN, HIGH);
    Serial.println(F("ALARM (TEMP EXCEEDS THRESHOLD!)"));
  } else {
    digitalWrite(LED_PIN, LOW);
    digitalWrite(BUZZER_PIN, LOW);
    Serial.println(F("NORMAL"));
  }
}
