#define SERVO_PIN 2

void setup() {
  Serial.begin(115200);

  pinMode(SERVO_PIN, OUTPUT);

  servoWrite(90);
}

void servoWrite(int angle) {
  angle = constrain(angle, 0, 180);

  // Convert angle to pulse width
  // 0° = 500 us
  // 180° = 2500 us
  int pulseWidth = map(angle, 0, 180, 500, 2500);

  // Servo needs ~50 Hz = 20 ms period
  digitalWrite(SERVO_PIN, HIGH);
  delayMicroseconds(pulseWidth);

  digitalWrite(SERVO_PIN, LOW);
  delayMicroseconds(20000 - pulseWidth);
}

void loop() {

  Serial.println("0 degrees");
  for (int i = 0; i < 25; i++) {
    servoWrite(0);
  }

  delay(500);

  Serial.println("90 degrees");
  for (int i = 0; i < 25; i++) {
    servoWrite(90);
  }

  delay(500);

  Serial.println("180 degrees");
  for (int i = 0; i < 25; i++) {
    servoWrite(180);
  }

  delay(500);
}