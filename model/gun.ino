#include <Servo.h>

Servo myServo;  // Create servo object

const int servoPin = 13;  // Pin connected to servo

void setup() {
  Serial.begin(9600);            // Start serial communication at 9600 baud
  myServo.attach(servoPin);      // Attach servo to pin 9
  myServo.write(50);             // Start at rest position (60 degrees)
  Serial.println("Servo ready!");
  delay(1000);
}

void loop() {
  // Check if data is available from serial
  if (Serial.available() > 0) {
    char input = Serial.read();  // Read the incoming byte

     if (input == '\n' || input == '\r') {
      return;
    }

      Serial.println(" - FIRE!");
      myServo.write(110);  // Move to fire position
      delay(500);          // Hold position
      myServo.write(50);   // Return to neutral
      delay(500);
    
    
    Serial.println("Complete. Ready for next trigger...");
  }
}