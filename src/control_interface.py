# -----------------------------------------------------------------------------
# Phase I & II: Raspberry Pi Control/Logging Interface (using lgpio for Pi 5)
# -----------------------------------------------------------------------------
# This script handles both reading human expert commands (Phase I: Data Logging)
# and sending autonomous commands (Phase II: Control Injection).
#
# NOTE: Requires a Logic Level Converter (5V -> 3.3V) for safe connection
# from the RC board taps to the Raspberry Pi GPIO pins.
# -----------------------------------------------------------------------------

import lgpio
import time
import math
import threading

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

# --- 2. LGPIO INITIALIZATION ---
# NOTE: lgpio doesn't require a separate daemon like pigpio
h = lgpio.gpiochip_open(0)
if h < 0:
    print("Error: Could not open GPIO chip.")
    exit()

# --- 3. PHASE I: DATA CAPTURE (READING PWM SIGNALS) ---

class RCReader:
    """Accurately reads PWM pulse width and period using lgpio callbacks."""
    def __init__(self, gpio_handle, pin, neutral_us):
        self.h = gpio_handle
        self.pin = pin
        self.neutral_us = neutral_us
        self.last_tick_rising = time.time_ns()
        self.pulse_width = 0 # Duration of the HIGH signal in microseconds
        self.period = 0      # Duration of the full cycle in microseconds
        self.lock = threading.Lock()
        
        # Set pin as input
        lgpio.gpio_claim_input(self.h, pin)
        # Set up callback for both rising and falling edges
        self.cb = lgpio.callback(self.h, pin, lgpio.BOTH_EDGES, self._cb)

    def _cb(self, chip, gpio, level, timestamp):
        """Hardware callback function executed on every signal edge."""
        with self.lock:
            if level == 1:  # Rising edge (start of pulse)
                # Calculate the full period (time from last rising edge to this one)
                self.period = (timestamp - self.last_tick_rising) / 1000  # Convert to microseconds
                self.last_tick_rising = timestamp
            
            elif level == 0:  # Falling edge (end of pulse)
                # Calculate the pulse width (time from last rising edge to this falling edge)
                self.pulse_width = (timestamp - self.last_tick_rising) / 1000  # Convert to microseconds
    
    def get_normalized_action(self):
        """
        Converts raw PWM data to a normalized action suitable for ML training.
        Steering: [-1.0, 1.0]. Throttle: [0.0, 1.0].
        """
        with self.lock:
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
        lgpio.gpio_free(self.h, self.pin)


# --- 4. PHASE II: AUTONOMOUS CONTROL (WRITING PWM SIGNALS) ---

def set_control_commands(normalized_steering, normalized_throttle):
    """
    Translates normalized ML actions to hardware PWM commands and injects them.
    """
    
    # --- Steering Command Generation (Pulse Width) ---
    target_steering_us = int(STEERING_NEUTRAL_US + normalized_steering * STEERING_RANGE_US)
    
    # Claim the steering pin as output and set PWM
    try:
        lgpio.gpio_claim_output(h, STEERING_PIN_GPIO)
        # For servo control, we need to generate PWM with specific pulse width
        # lgpio uses frequency and duty cycle, so we calculate duty cycle from pulse width
        duty_cycle = (target_steering_us / (1000000 / STEERING_FREQ_HZ)) * 100
        lgpio.tx_pwm(h, STEERING_PIN_GPIO, STEERING_FREQ_HZ, duty_cycle)
    except:
        pass  # Pin might already be claimed
    
    # --- Throttle Command Generation (Duty Cycle) ---
    target_duty_percent = max(0.0, min(1.0, normalized_throttle)) * THROTTLE_MAX_DUTY
    
    # Claim the throttle pin as output and set PWM
    try:
        lgpio.gpio_claim_output(h, THROTTLE_PIN_GPIO)
        lgpio.tx_pwm(h, THROTTLE_PIN_GPIO, THROTTLE_FREQ_HZ, target_duty_percent)
    except:
        pass  # Pin might already be claimed

    
# --- 5. EXAMPLE USAGE ---

def data_logging_example():
    """Phase I: Main loop for logging expert commands."""
    print("--- Starting Phase I: Expert Data Logging (Raspberry Pi) ---")
    
    steering_reader = RCReader(h, STEERING_PIN_GPIO, STEERING_NEUTRAL_US)
    throttle_reader = RCReader(h, THROTTLE_PIN_GPIO, STEERING_NEUTRAL_US)
    
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
        try:
            lgpio.tx_pwm(h, STEERING_PIN_GPIO, 0, 0)  # Stop PWM
            lgpio.tx_pwm(h, THROTTLE_PIN_GPIO, 0, 0)  # Stop PWM
        except:
            pass

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
        try:
            lgpio.tx_pwm(h, STEERING_PIN_GPIO, 0, 0)  # Stop PWM
            lgpio.tx_pwm(h, THROTTLE_PIN_GPIO, 0, 0)  # Stop PWM
        except:
            pass
        

if __name__ == '__main__':
    
    print("--- FTX Tracer Control Interface Initialized (Raspberry Pi) ---")

    # --- CHOOSE YOUR PHASE ---
    
    # 1. UNCOMMENT THIS LINE to start data logging (Phase I)
    data_logging_example()
    
    # 2. COMMENT OUT Phase I and UNCOMMENT this line for autonomous testing (Phase II)
    # autonomous_control_example()

    # Always call lgpio.gpiochip_close() when done
    lgpio.gpiochip_close(h)
    print("lgpio connection closed.")
