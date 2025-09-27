// PWM Messung mit Interrupts für 2 Kanäle
// Liest zwei PWM-Signale ein, bestimmt Frequenz und Duty-Cycle

// -------------------- Kanal 1 --------------------
const byte pwmPin1 = 2; // Pin für PWM Eingang (muss Interrupt-fähig sein)
volatile unsigned long lastRise1 = 0;
volatile unsigned long highTime1 = 0;
volatile unsigned long period1 = 0;
volatile bool newCycle1 = false;

// -------------------- Kanal 2 --------------------
const byte pwmPin2 = 3; // zweiter PWM-Eingang
volatile unsigned long lastRise2 = 0;
volatile unsigned long highTime2 = 0;
volatile unsigned long period2 = 0;
volatile bool newCycle2 = false;

void setup() {
  Serial.begin(115200);

  pinMode(pwmPin1, INPUT);
  pinMode(pwmPin2, INPUT);

  attachInterrupt(digitalPinToInterrupt(pwmPin1), handleInterrupt1, CHANGE);
  attachInterrupt(digitalPinToInterrupt(pwmPin2), handleInterrupt2, CHANGE);
}

void loop() {
  // -------------------- Kanal 1 --------------------
  if (newCycle1) {
    noInterrupts();
    unsigned long tHigh = highTime1;
    unsigned long tPeriod = period1;
    newCycle1 = false;
    interrupts();

    if (tPeriod > 0) {
      float freq = 1e6 / (float)tPeriod;             // Hz
      float duty = (tHigh * 100.0) / (float)tPeriod; // %
      Serial.print("Kanal 1: f = ");
      Serial.print(freq, 1);
      Serial.print(" Hz, duty = ");
      Serial.print(duty, 2);
      Serial.println(" %");
    }
  }

  // -------------------- Kanal 2 --------------------
  if (newCycle2) {
    noInterrupts();
    unsigned long tHigh = highTime2;
    unsigned long tPeriod = period2;
    newCycle2 = false;
    interrupts();

    if (tPeriod > 0) {
      float freq = 1e6 / (float)tPeriod;             // Hz
      float duty = (tHigh * 100.0) / (float)tPeriod; // %
      Serial.print("Kanal 2: f = ");
      Serial.print(freq, 1);
      Serial.print(" Hz, duty = ");
      Serial.print(duty, 2);
      Serial.println(" %");
    }
  }
}

// -------------------- ISR Kanal 1 --------------------
void handleInterrupt1() {
  static unsigned long riseTime = 0;
  unsigned long now = micros();

  if (digitalRead(pwmPin1) == HIGH) {
    if (riseTime > 0) {
      period1 = now - riseTime;
      newCycle1 = true;
    }
    riseTime = now;
    lastRise1 = now;
  } else {
    highTime1 = now - lastRise1;
  }
}

// -------------------- ISR Kanal 2 --------------------
void handleInterrupt2() {
  static unsigned long riseTime = 0;
  unsigned long now = micros();

  if (digitalRead(pwmPin2) == HIGH) {
    if (riseTime > 0) {
      period2 = now - riseTime;
      newCycle2 = true;
    }
    riseTime = now;
    lastRise2 = now;
  } else {
    highTime2 = now - lastRise2;
  }
}