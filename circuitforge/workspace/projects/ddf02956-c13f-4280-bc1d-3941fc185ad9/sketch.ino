#include <DHT.h>
#include <AdafruitUnifiedSensor.h>
#include <Servo.h>
#include <Wire.h>
#include <Potentiometer.h>

#define DHTPIN 4
#define DHTTYPE DHT22

DHT dht(DHTPIN, DHTTYPE);
Servo myservo;
Potentiometer potentiometer_10k(0, 0, 1023);

void setup() {
  Serial.begin(115200);
  dht.begin();
  myservo.attach(9);
  potentiometer_10k.attach(5);
}

void loop() {
  float t = dht.readTemperature(DHTTYPE);
  float h = dht.readHumidity();
  if (isnan(t) || isnan(h)) {
    Serial.println("Failed to read from DHT sensor!");
    return;
  }
  float tempC = t * 9/5 + 32;
  if (tempC > 30) {
    myservo.write(180);
  } else {
    myservo.write(0);
  }
  Serial.print("Temp: ");
  Serial.print(tempC);
  Serial.println(" C");
  Serial.println("");
  delay(2000);
}