// Enhanced PWM Reader for RC Car Data Collection
// Reads two PWM channels (steering + throttle) and sends formatted data via Serial
// Optimized for real-time data collection with timestamp synchronization

// -------------------- Configuration --------------------
const byte THROTTLE_PIN = 2;  // Pin for throttle PWM (900Hz, 0-70% duty)
const byte STEERING_PIN = 3;  // Pin for steering PWM (50Hz, 5-9.2% duty)
const unsigned long SAMPLE_RATE_MS = 33; // ~30Hz to match camera (33.33ms)

// -------------------- Global Variables - Throttle --------------------
volatile unsigned long throttle_lastRise = 0;
volatile unsigned long throttle_highTime = 0;
volatile unsigned long throttle_period = 0;
volatile bool throttle_newCycle = false;

// -------------------- Global Variables - Steering --------------------
volatile unsigned long steering_lastRise = 0;
volatile unsigned long steering_highTime = 0;
volatile unsigned long steering_period = 0;
volatile bool steering_newCycle = false;

// -------------------- Calibration Constants --------------------
// Throttle: 900Hz PWM, 0-70% duty cycle
const float THROTTLE_MIN_DUTY = 0.0;
const float THROTTLE_MAX_DUTY = 70.0;
const float THROTTLE_NEUTRAL_DUTY = 0.0;  // 0% = stopped

// Steering: 50Hz PWM, 5-9.2% duty cycle  
const float STEERING_MIN_DUTY = 5.0;      // 5% = Full Left
const float STEERING_NEUTRAL_DUTY = 7.0;  // 7% = Straight
const float STEERING_MAX_DUTY = 9.2;      // 9.2% = Full Right

// -------------------- Setup --------------------
void setup() {
  Serial.begin(115200);
  
  // Initialize pins
  pinMode(STEERING_PIN, INPUT);
  pinMode(THROTTLE_PIN, INPUT);
  
  // Attach interrupts
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
  
  // Sample at consistent rate
  if (currentTime - lastSampleTime >= SAMPLE_RATE_MS) {
    lastSampleTime = currentTime;
    
    // Read current values (atomic operations)
    noInterrupts();
    unsigned long throttle_pulse = throttle_highTime;
    unsigned long throttle_per = throttle_period;
    unsigned long steer_pulse = steering_highTime;
    unsigned long steer_per = steering_period;
    interrupts();
    
    // Calculate normalized values
    float throttle_normalized = calculateThrottleNormalized(throttle_pulse, throttle_per);
    float steer_normalized = calculateSteeringNormalized(steer_pulse, steer_per);
    
    // Send data in structured format
    sendDataPacket(currentTime, steer_normalized, throttle_normalized, 
                   steer_pulse, throttle_pulse, steer_per, throttle_per);
  }
}

// -------------------- Interrupt Handlers --------------------
void handleThrottleInterrupt() {
  static unsigned long lastRiseTime = 0;
  unsigned long now = micros();
  
  if (digitalRead(THROTTLE_PIN) == HIGH) {
    // Rising edge - calculate period and start new pulse
    if (lastRiseTime > 0 && now > lastRiseTime) {
      throttle_period = now - lastRiseTime;
      throttle_newCycle = true;
    }
    lastRiseTime = now;
    throttle_lastRise = now;
  } else {
    // Falling edge - calculate pulse width
    if (throttle_lastRise > 0 && now > throttle_lastRise) {
      throttle_highTime = now - throttle_lastRise;
    }
  }
}

void handleSteeringInterrupt() {
  static unsigned long riseTime = 0;
  unsigned long now = micros();
  
  if (digitalRead(STEERING_PIN) == HIGH) {
    // Rising edge - start of new period
    if (riseTime > 0) {
      steering_period = now - riseTime;
      steering_newCycle = true;
    }
    riseTime = now;
    steering_lastRise = now;
  } else {
    // Falling edge - end of pulse
    steering_highTime = now - steering_lastRise;
  }
}

// -------------------- Calculation Functions --------------------
float calculateThrottleNormalized(unsigned long pulseWidth, unsigned long period) {
  if (pulseWidth < 50 || period < 500) return 0.0; // Invalid signal
  
  // Calculate duty cycle percentage
  float dutyCycle = ((float)pulseWidth / (float)period) * 100.0;
  
  // Map 0-70% duty to 0.0-1.0 normalized (0.0 = stopped, 1.0 = full throttle)
  float normalized = dutyCycle / THROTTLE_MAX_DUTY;
  return constrain(normalized, 0.0, 1.0);
}

float calculateSteeringNormalized(unsigned long pulseWidth, unsigned long period) {
  if (pulseWidth < 50 || period < 10000) return 0.0; // Invalid signal
  
  // Calculate duty cycle percentage
  float dutyCycle = ((float)pulseWidth / (float)period) * 100.0;
  
  // Map 5-9.2% duty to -1.0 to +1.0 normalized
  // 5% = -1.0 (full left), 7% = 0.0 (straight), 9.2% = +1.0 (full right)
  float normalized = (dutyCycle - STEERING_NEUTRAL_DUTY) / (STEERING_MAX_DUTY - STEERING_NEUTRAL_DUTY) * (2.0/2.2);
  return constrain(normalized, -1.0, 1.0);
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