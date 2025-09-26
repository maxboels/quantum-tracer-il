# -----------------------------------------------------------------------------
# Phase I & II: Raspberry Pi Control/Logging Interface (using pigpio)
# -----------------------------------------------------------------------------
# This script handles both reading human expert commands (Phase I: Data Logging)
# and sending autonomous commands (Phase II: Control Injection).
#
# NOTE: Requires a Logic Level Converter (5V -> 3.3V) for safe connection
# from the RC board taps to the Raspberry Pi GPIO pins.
# -----------------------------------------------------------------------------

import pigpio
import time
import math

# --- 1. HARDWARE CONFIGURATION ---

# BCM (GPIO) Pin assignments on the Raspberry Pi
# !!! CONFIRM THESE PINS MATCH YOUR WIRING !!!
STEERING_PIN_GPIO = 18  # BCM 18: Steering (PWM Servo tap)
THROTTLE_PIN_GPIO = 23  # BCM 23: Throttle (PWM Drive tap)

# Confirmed PWM Signal Parameters (from oscilloscope analysis)
STEERING_NEUTRAL_US = 1491 # 7.0% Duty @ 47Hz
STEERING_RANGE_US = 450 # Approx. deviation from neutral for normalization (e.g., 1941 - 1491 = 450)
STEERING_FREQ_HZ = 47

THROTTLE_MAX_DUTY = 70.0 # Max 70% duty cycle for full throttle (0% is stop)
THROTTLE_FREQ_HZ = 985 # High frequency for motor control

# --- 2. PIGPIO INITIALIZATION ---
# NOTE: pigpio daemon MUST be running before execution: 'sudo pigpiod'
pi = pigpio.pi()
if not pi.connected:
    print("Error: Could not connect to pigpio daemon. Run 'sudo pigpiod'.")
    exit()

# --- 3. PHASE I: DATA CAPTURE (READING PWM SIGNALS) ---

class RCReader:
    """Accurately reads PWM pulse width and period using pigpio callbacks."""
    def __init__(self, pi_instance, pin, neutral_us):
        self.pi = pi_instance
        self.pin = pin
        self.neutral_us = neutral_us
        self.last_tick_rising = self.pi.get_current_tick()
        self.pulse_width = 0 # Duration of the HIGH signal in microseconds
        self.period = 0      # Duration of the full cycle in microseconds
        
        self.pi.set_mode(pin, pigpio.INPUT)
        # Callback triggers on both signal edges for accurate timing
        self.cb = self.pi.callback(pin, pigpio.EITHER_EDGE, self._cb)

    def _cb(self, pin, level, tick):
        """Hardware callback function executed on every signal edge."""
        if level == 1:  # Rising edge (start of pulse)
            # Calculate the full period (time from last rising edge to this one)
            self.period = pigpio.tickDiff(self.last_tick_rising, tick)
            self.last_tick_rising = tick
        
        elif level == 0:  # Falling edge (end of pulse)
            # Calculate the pulse width (time from last rising edge to this falling edge)
            self.pulse_width = pigpio.tickDiff(self.last_tick_rising, tick)
    
    def get_normalized_action(self):
        """
        Converts raw PWM data to a normalized action suitable for ML training.
        Steering: [-1.0, 1.0]. Throttle: [0.0, 1.0].
        """
        
        if self.pin == STEERING_PIN_GPIO:
            # STEERING: Pulse Width (us) based (47Hz)
            if self.pulse_width < 10: return 0.0 # Ignore noise near zero
            
            # Normalize around neutral (1491 us)
            normalized = (self.pulse_width - self.neutral_us) / STEERING_RANGE_US
            return max(-1.0, min(1.0, normalized)) # Clamp to safe range [-1.0, 1.0]
        
        elif self.pin == THROTTLE_PIN_GPIO:
            # THROTTLE: Duty Cycle (%) based (985Hz)
            if self.pulse_width < 10 or self.period < 10: 
                return 0.0 # Assume stop (0%) if signal is missing or noisy
            
            # Calculate Duty Cycle: (Pulse Width / Period)
            duty_cycle_percent = (self.pulse_width / self.period) * 100
            
            # Normalize to 0.0 (0% duty) to 1.0 (70% duty)
            normalized = duty_cycle_percent / THROTTLE_MAX_DUTY
            return max(0.0, min(1.0, normalized)) # Clamp to safe range [0.0, 1.0]

        return 0.0

    def cancel(self):
        self.cb.cancel()


# --- 4. PHASE II: AUTONOMOUS CONTROL (WRITING PWM SIGNALS) ---

def set_control_commands(normalized_steering, normalized_throttle):
    """
    Translates normalized ML actions to hardware PWM commands and injects them.
    """
    
    # --- Steering Command Generation (Pulse Width) ---
    target_steering_us = int(STEERING_NEUTRAL_US + normalized_steering * STEERING_RANGE_US)
    
    # 1. Set frequency for the SERVO pin (47Hz)
    pi.set_PWM_frequency(STEERING_PIN_GPIO, STEERING_FREQ_HZ)
    # 2. Set the pulse width (in microseconds)
    pi.set_servo_pulsewidth(STEERING_PIN_GPIO, target_steering_us)
    
    
    # --- Throttle Command Generation (Duty Cycle) ---
    target_duty_percent = max(0.0, min(1.0, normalized_throttle)) * THROTTLE_MAX_DUTY
    # Pigpio uses a range of 0 to 1,000,000 for duty cycle
    target_duty_pigpio = int(target_duty_percent * 10000)
    
    # 1. Set frequency for the DRIVE pin (985Hz)
    pi.set_PWM_frequency(THROTTLE_PIN_GPIO, THROTTLE_FREQ_HZ)
    # 2. Set the duty cycle 
    pi.set_PWM_dutycycle(THROTTLE_PIN_GPIO, target_duty_pigpio)

    
# --- 5. EXAMPLE USAGE ---

def data_logging_example():
    """Phase I: Main loop for logging expert commands."""
    print("--- Starting Phase I: Expert Data Logging (Raspberry Pi) ---")
    
    steering_reader = RCReader(pi, STEERING_PIN_GPIO, STEERING_NEUTRAL_US)
    throttle_reader = RCReader(pi, THROTTLE_PIN_GPIO, STEERING_NEUTRAL_US)
    
    print(f"Logging actions at {1/0.02} Hz. Hit CTRL+C to stop.")
    print("--- (Raw Pulse Width/Duty Cycle will vary based on RC Transmitter movement) ---")

    try:
        while True:
            # 1. Read Action
            steer_action = steering_reader.get_normalized_action()
            throttle_action = throttle_reader.get_normalized_action()
            
            # 2. Capture Vision Data (Integration point for your camera code)
            # image_frame = capture_camera_frame() 
            
            # 3. Log Data Point (This output should be piped/saved to a file)
            print(f"Time: {time.time():.2f} | "
                  f"STEER: {steer_action:.4f} (Raw: {steering_reader.pulse_width} us) | "
                  f"THROTTLE: {throttle_action:.4f} (Duty: {(throttle_reader.pulse_width / throttle_reader.period * 100) if throttle_reader.period > 0 else 0:.1f} %)")
            
            time.sleep(0.02) # Target 50Hz refresh rate
            
    except KeyboardInterrupt:
        print("\nLogging successfully stopped.")
    finally:
        # Clean up the readers
        steering_reader.cancel()
        throttle_reader.cancel()
        # Clean up the control pins in case we ever used them
        set_control_commands(0.0, 0.0) 
        pi.set_servo_pulsewidth(STEERING_PIN_GPIO, 0)
        pi.set_PWM_dutycycle(THROTTLE_PIN_GPIO, 0)

def autonomous_control_example():
    """Phase II: Main loop for testing autonomous command injection."""
    print("--- Starting Phase II: Autonomous Control Test (RC Transmitter OFF) ---")
    
    try:
        # Example 1: Straight and Half Speed 
        print("Command 1: Straight (0.0) and Half Speed (0.5)...")
        set_control_commands(0.0, 0.5)
        time.sleep(3) 

        # Example 2: Full Left and Quarter Speed 
        print("Command 2: Full Left (-1.0) and Quarter Speed (0.25)...")
        set_control_commands(-1.0, 0.25)
        time.sleep(3)
        
        # Example 3: Full Right and Full Speed 
        print("Command 3: Full Right (1.0) and Full Speed (1.0)...")
        set_control_commands(1.0, 1.0)
        time.sleep(3)

    except KeyboardInterrupt:
        pass
    finally:
        # Crucial Safety Stop
        print("Stopping all motors and resetting pins.")
        set_control_commands(0.0, 0.0) 
        pi.set_servo_pulsewidth(STEERING_PIN_GPIO, 0)
        pi.set_PWM_dutycycle(THROTTLE_PIN_GPIO, 0)
        

if __name__ == '__main__':
    
    print("--- FTX Tracer Control Interface Initialized (Raspberry Pi) ---")

    # --- CHOOSE YOUR PHASE ---
    
    # 1. UNCOMMENT THIS LINE to start data logging (Phase I)
    data_logging_example()
    
    # 2. COMMENT OUT Phase I and UNCOMMENT this line for autonomous testing (Phase II)
    # autonomous_control_example()

    # Always call pi.stop() when done
    pi.stop()
    print("Pigpio connection closed.")
