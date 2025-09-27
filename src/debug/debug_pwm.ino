// Debug PWM Reader - Shows detailed interrupt activity on both pins
// This will help us understand why throttle isn't working

const byte THROTTLE_PIN = 2;
const byte STEERING_PIN = 3;

// Throttle counters
volatile unsigned long throttle_interrupts = 0;
volatile unsigned long throttle_high_edges = 0;
volatile unsigned long throttle_low_edges = 0;
volatile unsigned long throttle_last_high = 0;
volatile unsigned long throttle_last_low = 0;

// Steering counters  
volatile unsigned long steering_interrupts = 0;
volatile unsigned long steering_high_edges = 0;
volatile unsigned long steering_low_edges = 0;
volatile unsigned long steering_last_high = 0;
volatile unsigned long steering_last_low = 0;

void setup() {
  Serial.begin(115200);
  
  pinMode(THROTTLE_PIN, INPUT);
  pinMode(STEERING_PIN, INPUT);
  
  // Attach interrupts
  attachInterrupt(digitalPinToInterrupt(THROTTLE_PIN), throttleISR, CHANGE);
  attachInterrupt(digitalPinToInterrupt(STEERING_PIN), steeringISR, CHANGE);
  
  Serial.println("DEBUG_PWM_READY");
  Serial.println("Monitoring interrupt activity on both pins...");
  Serial.println("Move throttle and steering to see interrupt counts");
  Serial.println("Format: time,throttle_ints,throttle_highs,throttle_lows,steering_ints,steering_highs,steering_lows");
}

void throttleISR() {
  throttle_interrupts++;
  unsigned long now = micros();
  
  if (digitalRead(THROTTLE_PIN) == HIGH) {
    throttle_high_edges++;
    throttle_last_high = now;
  } else {
    throttle_low_edges++;
    throttle_last_low = now;
  }
}

void steeringISR() {
  steering_interrupts++;
  unsigned long now = micros();
  
  if (digitalRead(STEERING_PIN) == HIGH) {
    steering_high_edges++;
    steering_last_high = now;
  } else {
    steering_low_edges++;
    steering_last_low = now;
  }
}

void loop() {
  static unsigned long lastReport = 0;
  unsigned long now = millis();
  
  if (now - lastReport >= 1000) {  // Report every second
    lastReport = now;
    
    // Read all counters atomically
    noInterrupts();
    unsigned long t_ints = throttle_interrupts;
    unsigned long t_highs = throttle_high_edges;
    unsigned long t_lows = throttle_low_edges;
    unsigned long s_ints = steering_interrupts;
    unsigned long s_highs = steering_high_edges;
    unsigned long s_lows = steering_low_edges;
    
    // Reset counters
    throttle_interrupts = 0;
    throttle_high_edges = 0;
    throttle_low_edges = 0;
    steering_interrupts = 0;
    steering_high_edges = 0;
    steering_low_edges = 0;
    interrupts();
    
    // Report results
    Serial.print(now);
    Serial.print(",");
    Serial.print(t_ints);
    Serial.print(",");
    Serial.print(t_highs);
    Serial.print(",");
    Serial.print(t_lows);
    Serial.print(",");
    Serial.print(s_ints);
    Serial.print(",");
    Serial.print(s_highs);
    Serial.print(",");
    Serial.print(s_lows);
    Serial.println();
    
    // Also show pin states
    Serial.print("PIN_STATES: Throttle=");
    Serial.print(digitalRead(THROTTLE_PIN));
    Serial.print(", Steering=");
    Serial.println(digitalRead(STEERING_PIN));
  }
}