// Enhanced PWM Reader with Control Output for Remote Inference
// Reads PWM channels AND can output control signals for autonomous driving
// Supports both data collection mode and autonomous control mode

// -------------------- Configuration --------------------
const byte THROTTLE_PIN = 2;  // Pin for throttle PWM input
const byte STEERING_PIN = 3;  // Pin for steering PWM input
const unsigned long SAMPLE_RATE_MS = 33; // ~30Hz to match camera

// Output pins for autonomous control (if needed)
const byte THROTTLE_OUTPUT_PIN = 9;   // PWM output for throttle control
const byte STEERING_OUTPUT_PIN = 10;  // PWM output for steering control

// -------------------- Global Variables - Input Reading --------------------
volatile unsigned long throttle_lastRise = 0;
volatile unsigned long throttle_highTime = 0;
volatile unsigned long throttle_period = 0;
volatile bool throttle_newCycle = false;

volatile unsigned long steering_lastRise = 0;
volatile unsigned long steering_highTime = 0;
volatile unsigned long steering_period = 0;
volatile bool steering_newCycle = false;

// -------------------- Global Variables - Control Output --------------------
bool autonomous_mode = false;
float target_steering = 0.0;   // [-1.0, 1.0] target from remote inference
float target_throttle = 0.0;   // [0.0, 1.0] target from remote inference

// -------------------- Calibration Constants --------------------
// Throttle: 900Hz PWM, 0-70% duty cycle
const float THROTTLE_MIN_DUTY = 0.0;
const float THROTTLE_MAX_DUTY = 70.0;
const float THROTTLE_NEUTRAL_DUTY = 0.0;

// Steering: 50Hz PWM, 5-9.2% duty cycle  
const float STEERING_MIN_DUTY = 5.0;      // 5% = Full Left
const float STEERING_NEUTRAL_DUTY = 7.0;  // 7% = Straight
const float STEERING_MAX_DUTY = 9.2;      // 9.2% = Full Right

// Output PWM parameters for control
const int SERVO_MIN_PULSE = 1000;  // 1ms pulse width
const int SERVO_MAX_PULSE = 2000;  // 2ms pulse width
const int SERVO_NEUTRAL_PULSE = 1500; // 1.5ms neutral

// -------------------- Setup --------------------
void setup() {
  Serial.begin(115200);
  
  // Initialize input pins
  pinMode(STEERING_PIN, INPUT);
  pinMode(THROTTLE_PIN, INPUT);
  
  // Initialize output pins for autonomous control
  pinMode(THROTTLE_OUTPUT_PIN, OUTPUT);
  pinMode(STEERING_OUTPUT_PIN, OUTPUT);
  
  // Attach interrupts for input reading
  attachInterrupt(digitalPinToInterrupt(THROTTLE_PIN), handleThrottleInterrupt, CHANGE);
  attachInterrupt(digitalPinToInterrupt(STEERING_PIN), handleSteeringInterrupt, CHANGE);
  
  // Send initialization message
  Serial.println("ARDUINO_READY");
  Serial.flush();
}

// -------------------- Main Loop --------------------
void loop() {
  static unsigned long lastSampleTime = 0;
  unsigned long currentTime = millis();
  
  // Check for incoming control commands
  if (Serial.available()) {
    String command = Serial.readStringUntil('\n');
    processControlCommand(command);
  }
  
  // Sample and send sensor data at consistent rate
  if (currentTime - lastSampleTime >= SAMPLE_RATE_MS) {
    // Read current PWM values
    float steer_norm = 0.0;
    float throttle_norm = 0.0;
    unsigned long steer_raw = 0, throttle_raw = 0;
    unsigned long steer_period_val = 0, throttle_period_val = 0;
    
    // Safely read steering data
    noInterrupts();
    if (steering_newCycle) {
      steer_norm = calculateSteeringNormalized(steering_highTime, steering_period);
      steer_raw = steering_highTime;
      steer_period_val = steering_period;
      steering_newCycle = false;
    }
    interrupts();
    
    // Safely read throttle data
    noInterrupts();
    if (throttle_newCycle) {
      throttle_norm = calculateThrottleNormalized(throttle_highTime, throttle_period);
      throttle_raw = throttle_highTime;
      throttle_period_val = throttle_period;
      throttle_newCycle = false;
    }
    interrupts();
    
    // Send sensor data
    sendDataPacket(currentTime, steer_norm, throttle_norm, 
                   steer_raw, throttle_raw, steer_period_val, throttle_period_val);
    
    // Update autonomous control outputs if in autonomous mode
    if (autonomous_mode) {
      updateControlOutputs();
    }
    
    lastSampleTime = currentTime;
  }
}

// -------------------- Control Command Processing --------------------
void processControlCommand(String command) {
  command.trim();
  
  if (command.startsWith("CTRL,")) {
    // Control command: CTRL,steering,throttle
    int firstComma = command.indexOf(',', 5);
    int secondComma = command.indexOf(',', firstComma + 1);
    
    if (firstComma > 0 && secondComma > 0) {
      float steering = command.substring(5, firstComma).toFloat();
      float throttle = command.substring(firstComma + 1, secondComma).toFloat();
      
      // Clamp values to safe ranges
      target_steering = constrain(steering, -1.0, 1.0);
      target_throttle = constrain(throttle, 0.0, 1.0);
      
      autonomous_mode = true;
      
      Serial.print("CTRL_ACK,");
      Serial.print(target_steering, 4);
      Serial.print(",");
      Serial.print(target_throttle, 4);
      Serial.println();
    }
  }
  else if (command.startsWith("MODE,")) {
    // Mode command: MODE,AUTO or MODE,MANUAL
    if (command.indexOf("AUTO") > 0) {
      autonomous_mode = true;
      Serial.println("MODE_ACK,AUTO");
    } else if (command.indexOf("MANUAL") > 0) {
      autonomous_mode = false;
      // Set outputs to neutral/safe positions
      target_steering = 0.0;
      target_throttle = 0.0;
      updateControlOutputs();
      Serial.println("MODE_ACK,MANUAL");
    }
  }
  else if (command.startsWith("STATUS")) {
    // Status request
    Serial.print("STATUS,");
    Serial.print(autonomous_mode ? "AUTO" : "MANUAL");
    Serial.print(",");
    Serial.print(target_steering, 4);
    Serial.print(",");
    Serial.print(target_throttle, 4);
    Serial.println();
  }
}

// -------------------- Control Output --------------------
void updateControlOutputs() {
  // Convert normalized values to servo pulse widths
  int steering_pulse = map(target_steering * 1000, -1000, 1000, SERVO_MIN_PULSE, SERVO_MAX_PULSE);
  int throttle_pulse = map(target_throttle * 1000, 0, 1000, SERVO_NEUTRAL_PULSE, SERVO_MAX_PULSE);
  
  // Output PWM signals (50Hz servo signals)
  servo_write(STEERING_OUTPUT_PIN, steering_pulse);
  servo_write(THROTTLE_OUTPUT_PIN, throttle_pulse);
}

void servo_write(int pin, int pulse_width) {
  // Generate 50Hz PWM signal with specified pulse width
  // This is a simple implementation - you might want to use the Servo library instead
  digitalWrite(pin, HIGH);
  delayMicroseconds(pulse_width);
  digitalWrite(pin, LOW);
  // Note: This blocks execution, consider using timer-based PWM for better performance
}

// -------------------- Interrupt Handlers (Unchanged) --------------------
void handleThrottleInterrupt() {
  static unsigned long lastRiseTime = 0;
  unsigned long now = micros();
  
  if (digitalRead(THROTTLE_PIN) == HIGH) {
    // Rising edge
    if (lastRiseTime > 0) {
      throttle_period = now - lastRiseTime;
    }
    lastRiseTime = now;
  } else {
    // Falling edge
    if (lastRiseTime > 0) {
      throttle_highTime = now - lastRiseTime;
      throttle_newCycle = true;
    }
  }
}

void handleSteeringInterrupt() {
  static unsigned long riseTime = 0;
  unsigned long now = micros();
  
  if (digitalRead(STEERING_PIN) == HIGH) {
    // Rising edge  
    if (riseTime > 0) {
      steering_period = now - riseTime;
    }
    riseTime = now;
  } else {
    // Falling edge
    if (riseTime > 0) {
      steering_highTime = now - riseTime;
      steering_newCycle = true;
    }
  }
}

// -------------------- Calculation Functions (Unchanged) --------------------
float calculateThrottleNormalized(unsigned long pulseWidth, unsigned long period) {
  if (period == 0) return 0.0;
  
  float dutyPercent = (float(pulseWidth) / float(period)) * 100.0;
  float normalized = (dutyPercent - THROTTLE_MIN_DUTY) / (THROTTLE_MAX_DUTY - THROTTLE_MIN_DUTY);
  
  return constrain(normalized, 0.0, 1.0);
}

float calculateSteeringNormalized(unsigned long pulseWidth, unsigned long period) {
  if (period == 0) return 0.0;
  
  float dutyPercent = (float(pulseWidth) / float(period)) * 100.0;
  float normalized = (dutyPercent - STEERING_NEUTRAL_DUTY) / 
                     ((STEERING_MAX_DUTY - STEERING_MIN_DUTY) / 2.0);
  
  return constrain(normalized, -1.0, 1.0);
}

// -------------------- Communication (Unchanged) --------------------
void sendDataPacket(unsigned long timestamp, float steer_norm, float throttle_norm,
                   unsigned long steer_raw, unsigned long throttle_raw,
                   unsigned long steer_period, unsigned long throttle_period) {
  
  Serial.print("DATA,");
  Serial.print(timestamp);
  Serial.print(",");
  Serial.print(steer_norm, 4);
  Serial.print(",");
  Serial.print(throttle_norm, 4);
  Serial.print(",");
  Serial.print(steer_raw);
  Serial.print(",");
  Serial.print(throttle_raw);
  Serial.print(",");
  Serial.print(steer_period);
  Serial.print(",");
  Serial.print(throttle_period);
  Serial.println();
  Serial.flush();
}