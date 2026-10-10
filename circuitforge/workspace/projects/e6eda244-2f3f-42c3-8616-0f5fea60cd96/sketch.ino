#include <DHT.h>
#include <Adafruit Unified Sensor.h>
#include <Wire.h>

#define DHTPIN 4
#define DHTTYPE DHT22

DHT dht(DHTPIN, DHTTYPE);

void setup() {
  Serial.begin(115200);
  dht.begin();
}

void loop() {
  float t = dht.readTemperature(DHTTYPE);
  if (isnan(t)) {
    Serial.println("Failed to read from DHT sensor!");
    return;
  }
  if (t > 30.0) {
    digitalWrite(led_1, HIGH);
  } else {
    digitalWrite(led_1, LOW);
  }
  Serial.print("Temperature: ");
  Serial.print(t);
  Serial.println(" C");
  delay(2000);
}