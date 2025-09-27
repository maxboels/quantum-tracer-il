// Enhanced PWM Reader for RC Car Data Collection
// Reads two PWM channels (steering + throttle) and sends formatted data via Serial
// Optimized for real-time data collection with timestamp synchronization

// -------------------- Configuration --------------------
const byte STEERING_PIN = 2;  // Pin for steering PWM (interrupt capable)
const byte THROTTLE_PIN = 3;  // Pin for throttle PWM (interrupt capable)
const unsigned long SAMPLE_RATE_MS = 33; // ~30Hz to match camera (33.33ms)

// -------------------- Global Variables - Steering --------------------
volatile unsigned long steering_lastRise = 0;
volatile unsigned long steering_pulseWidth = 0;
volatile unsigned long steering_period = 0;
volatile bool steering_newData = false;

// -------------------- Global Variables - Throttle --------------------
volatile unsigned long throttle_lastRise = 0;
volatile unsigned long throttle_pulseWidth = 0;
volatile unsigned long throttle_period = 0;
volatile bool throttle_newData = false;

// -------------------- Calibration Constants --------------------
const unsigned long STEERING_NEUTRAL_US = 1491;
const unsigned long STEERING_RANGE_US = 450;  // Full range from neutral
const float THROTTLE_MAX_DUTY = 70.0;         // Maximum expected duty cycle

// -------------------- Setup --------------------
void setup() {
  Serial.begin(115200);
  
  // Initialize pins
  pinMode(STEERING_PIN, INPUT);
  pinMode(THROTTLE_PIN, INPUT);
  
  // Attach interrupts
  attachInterrupt(digitalPinToInterrupt(STEERING_PIN), handleSteeringInterrupt, CHANGE);
  attachInterrupt(digitalPinToInterrupt(THROTTLE_PIN), handleThrottleInterrupt, CHANGE);
  
  // Send initialization message
  Serial.println("ARDUINO_READY");
  Serial.flush();
}

// -------------------- Main Loop --------------------
void loop() {
  static unsigned long lastSampleTime = 0;
  unsigned long currentTime = millis();
  
  // Sample at consistent rate
  if (currentTime - lastSampleTime >= SAMPLE_RATE_MS) {
    lastSampleTime = currentTime;
    
    // Read current values (atomic operations)
    noInterrupts();
    unsigned long steer_pulse = steering_pulseWidth;
    unsigned long steer_period = steering_period;
    unsigned long throttle_pulse = throttle_pulseWidth;
    unsigned long throttle_period = throttle_period;
    interrupts();
    
    // Calculate normalized values
    float steer_normalized = calculateSteeringNormalized(steer_pulse);
    float throttle_normalized = calculateThrottleNormalized(throttle_pulse, throttle_period);
    
    // Send data in structured format
    sendDataPacket(currentTime, steer_normalized, throttle_normalized, 
                   steer_pulse, throttle_pulse, steer_period, throttle_period);
  }
}

// -------------------- Interrupt Handlers --------------------
void handleSteeringInterrupt() {
  static unsigned long lastRiseTime = 0;
  unsigned long currentTime = micros();
  
  if (digitalRead(STEERING_PIN) == HIGH) {
    // Rising edge - start of new period
    if (lastRiseTime > 0) {
      steering_period = currentTime - lastRiseTime;
    }
    lastRiseTime = currentTime;
    steering_lastRise = currentTime;
  } else {
    // Falling edge - end of pulse
    if (steering_lastRise > 0) {
      steering_pulseWidth = currentTime - steering_lastRise;
      steering_newData = true;
    }
  }
}

void handleThrottleInterrupt() {
  static unsigned long lastRiseTime = 0;
  unsigned long currentTime = micros();
  
  if (digitalRead(THROTTLE_PIN) == HIGH) {
    // Rising edge - start of new period
    if (lastRiseTime > 0) {
      throttle_period = currentTime - lastRiseTime;
    }
    lastRiseTime = currentTime;
    throttle_lastRise = currentTime;
  } else {
    // Falling edge - end of pulse
    if (throttle_lastRise > 0) {
      throttle_pulseWidth = currentTime - throttle_lastRise;
      throttle_newData = true;
    }
  }
}

// -------------------- Calculation Functions --------------------
float calculateSteeringNormalized(unsigned long pulseWidth) {
  if (pulseWidth < 100) return 0.0; // Invalid signal
  
  // Convert to normalized range [-1.0, 1.0]
  float normalized = (float)(pulseWidth - STEERING_NEUTRAL_US) / (float)STEERING_RANGE_US;
  return constrain(normalized, -1.0, 1.0);
}

float calculateThrottleNormalized(unsigned long pulseWidth, unsigned long period) {
  if (pulseWidth < 100 || period < 100) return 0.0; // Invalid signal
  
  // Calculate duty cycle percentage
  float dutyCycle = ((float)pulseWidth / (float)period) * 100.0;
  
  // Normalize to [0.0, 1.0] range
  float normalized = dutyCycle / THROTTLE_MAX_DUTY;
  return constrain(normalized, 0.0, 1.0);
}

// -------------------- Communication --------------------
void sendDataPacket(unsigned long timestamp, float steer_norm, float throttle_norm,
                   unsigned long steer_raw, unsigned long throttle_raw,
                   unsigned long steer_period, unsigned long throttle_period) {
  
  // Send data in CSV-like format for easy parsing
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
  Serial.flush(); // Ensure immediate transmission
}