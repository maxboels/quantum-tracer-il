// Simple Pin Diagnostic - Check if ANY signal exists on Pin 2
// This will help us determine if the throttle channel is physically connected

const byte THROTTLE_PIN = 2;
const byte STEERING_PIN = 3;

volatile unsigned long throttle_changes = 0;
volatile unsigned long steering_changes = 0;

void setup() {
  Serial.begin(115200);
  
  pinMode(THROTTLE_PIN, INPUT);
  pinMode(STEERING_PIN, INPUT);
  
  // Attach interrupts to count ANY change
  attachInterrupt(digitalPinToInterrupt(THROTTLE_PIN), throttleChange, CHANGE);
  attachInterrupt(digitalPinToInterrupt(STEERING_PIN), steeringChange, CHANGE);
  
  Serial.println("PIN_DIAGNOSTIC_READY");
  Serial.println("Monitoring Pin 2 (Throttle) and Pin 3 (Steering) for ANY signal changes...");
  Serial.println("Format: time,pin2_changes,pin3_changes,pin2_state,pin3_state");
}

void throttleChange() {
  throttle_changes++;
}

void steeringChange() {
  steering_changes++;
}

void loop() {
  static unsigned long lastReport = 0;
  unsigned long now = millis();
  
  if (now - lastReport >= 1000) {  // Report every second
    lastReport = now;
    
    // Read current states
    int pin2_state = digitalRead(THROTTLE_PIN);
    int pin3_state = digitalRead(STEERING_PIN);
    
    // Get change counts atomically
    noInterrupts();
    unsigned long t_changes = throttle_changes;
    unsigned long s_changes = steering_changes;
    // Reset counters
    throttle_changes = 0;
    steering_changes = 0;
    interrupts();
    
    Serial.print(now);
    Serial.print(",");
    Serial.print(t_changes);
    Serial.print(",");
    Serial.print(s_changes);
    Serial.print(",");
    Serial.print(pin2_state);
    Serial.print(",");
    Serial.print(pin3_state);
    Serial.println();
  }
}