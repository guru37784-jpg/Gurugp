#include <Servo.h>

// AI SMART DUSTBIN - ARDUINO UNO FIRMWARE
// Sensors:
// S1: TRIG D4, ECHO D5 (garbage approach distance)
// S2: TRIG D6, ECHO D7 (bin fullness)
// S3: TRIG D8, ECHO D9 (bin fullness)
//
// Motors:
// Motor 1 MG995 signal D10 (paper sorting)
// Motor 2 9g servo signal D3 (plastic sorting)
//
// Serial: 9600 baud
// Expected output: S1:xx.x,S2:xx.x,S3:xx.x

Servo motor1;
Servo motor2;

const byte MOTOR1_PIN = 10;
const byte MOTOR2_PIN = 3;

const byte TRIG1_PIN = 4;
const byte ECHO1_PIN = 5;
const byte TRIG2_PIN = 6;
const byte ECHO2_PIN = 7;
const byte TRIG3_PIN = 8;
const byte ECHO3_PIN = 9;

unsigned long lastSensorRead = 0;
const unsigned long SENSOR_INTERVAL_MS = 300;

float readDistanceCm(byte trigPin, byte echoPin) {
  digitalWrite(trigPin, LOW);
  delayMicroseconds(2);

  digitalWrite(trigPin, HIGH);
  delayMicroseconds(10);
  digitalWrite(trigPin, LOW);

  unsigned long duration = pulseIn(echoPin, HIGH, 30000UL);

  if (duration == 0) {
    return -1.0;
  }

  return (duration * 0.0343f) / 2.0f;
}

void handleSerialCommands() {
  if (!Serial.available()) {
    return;
  }

  String command = Serial.readStringUntil('\n');
  command.trim();
  command.toLowerCase();

  if (command == "m1 90") {
    motor1.write(90);
    Serial.println("ACK:MOTOR1_90");
  }
  else if (command == "m2 90") {
    motor2.write(90);
    Serial.println("ACK:MOTOR2_90");
  }
  else if (command == "m1 0") {
    motor1.write(0);
    Serial.println("ACK:MOTOR1_HOME");
  }
  else if (command == "m2 0") {
    motor2.write(0);
    Serial.println("ACK:MOTOR2_HOME");
  }
  else if (command == "home") {
    motor1.write(0);
    motor2.write(0);
    Serial.println("ACK:BOTH_HOME");
  }
  else {
    Serial.print("UNKNOWN COMMAND:");
    Serial.println(command);
  }
}

void setup() {
  Serial.begin(9600);
  Serial.setTimeout(100);

  pinMode(TRIG1_PIN, OUTPUT);
  pinMode(ECHO1_PIN, INPUT);
  pinMode(TRIG2_PIN, OUTPUT);
  pinMode(ECHO2_PIN, INPUT);
  pinMode(TRIG3_PIN, OUTPUT);
  pinMode(ECHO3_PIN, INPUT);

  digitalWrite(TRIG1_PIN, LOW);
  digitalWrite(TRIG2_PIN, LOW);
  digitalWrite(TRIG3_PIN, LOW);

  // Attach motor outputs. MG995 must be safely powered and tested.
  motor1.attach(MOTOR1_PIN);
  motor2.attach(MOTOR2_PIN);

  motor1.write(0);
  motor2.write(0);

  Serial.println("SMART BIN READY");
}

void loop() {
  handleSerialCommands();

  if (millis() - lastSensorRead >= SENSOR_INTERVAL_MS) {
    lastSensorRead = millis();

    float s1 = readDistanceCm(TRIG1_PIN, ECHO1_PIN);
    delay(35);
    float s2 = readDistanceCm(TRIG2_PIN, ECHO2_PIN);
    delay(35);
    float s3 = readDistanceCm(TRIG3_PIN, ECHO3_PIN);

    Serial.print("S1:");
    Serial.print(s1, 1);
    Serial.print(",S2:");
    Serial.print(s2, 1);
    Serial.print(",S3:");
    Serial.println(s3, 1);
  }
}
