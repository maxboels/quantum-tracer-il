# -----------------------------------------------------------------------------
# ACT AUTONOMOUS INFERENCE: FTX TRACER TRUGGY (Phase II)
# -----------------------------------------------------------------------------
# This script executes the trained ACT policy in a real-time 30 Hz control loop.
# It captures an image, runs inference, and writes PWM commands via pigpio.
#
# Optimization Note: The actual model inference (Step 2) will use a highly 
# optimized framework like ONNX Runtime or the Hailo Runtime for speed.
# -----------------------------------------------------------------------------

import pigpio
import time
import numpy as np
import random 

# --- 1. HARDWARE & TIMING CONFIGURATION ---

# GPIO Pin assignments on the Raspberry Pi 5 (Output Pins)
STEERING_PIN_GPIO = 18  # BCM 18: Steering (PWM Servo tap)
THROTTLE_PIN_GPIO = 23  # BCM 23: Throttle (PWM Drive tap)

# Confirmed PWM Signal Parameters (DO NOT CHANGE)
STEERING_NEUTRAL_US = 1491
STEERING_RANGE_US = 450 # (1941 - 1491 = 450) or (1491 - 1041 = 450)
THROTTLE_MAX_DUTY = 70.0 

# Synchronization
CAMERA_FPS = 30.0  # Target control loop rate
CONTROL_INTERVAL = 1.0 / CAMERA_FPS # Required time delay (approx 0.0333 seconds)

# --- 2. PIGPIO INITIALIZATION ---
pi = pigpio.pi()
if not pi.connected:
    print("Error: Could not connect to pigpio daemon. Run 'sudo pigpiod'.")
    exit()

# --- 3. MODEL AND INFERENCE SETUP (MOCK CLASS) ---

class MockACTPolicy:
    """
    Placeholder for the optimized ACT model inference.
    
    In a production system, this class would load the optimized model (e.g., 
    a compiled Hailo .hef model or an ONNX model) and run inference via the 
    Hailo SDK or ONNX Runtime.
    """
    def __init__(self):
        print("Model: Initializing Mock ACT Policy (FP32/INT8 optimization assumed).")
        # In production: Load optimized model here (e.g., ONNXRuntime.InferenceSession)
        
    def predict_action(self, image_tensor):
        """
        MOCK: Simulates the model predicting a normalized steering and throttle command.
        
        Args:
            image_tensor (np.ndarray): The 1080p frame from the camera.
            
        Returns:
            tuple: (steering_action, throttle_action)
        """
        # --- MOCK PREDICTION: REPLACE WITH ACTUAL INFERENCE CODE ---
        # For testing, we simulate a simple wandering behavior
        
        # Steering: Randomly wander from -0.5 (left) to 0.5 (right)
        steering = random.uniform(-0.5, 0.5) 
        # Throttle: Maintain a constant slow speed (0.35)
        throttle = 0.35 

        # --- END MOCK PREDICTION ---
        
        return steering, throttle
    
# --- 4. PWM TRANSLATION AND CONTROL FUNCTIONS ---

def set_control_commands(normalized_steer, normalized_throttle):
    """
    Converts normalized ML actions back into raw PWM signals and injects them.
    This is the core control injection logic.
    """
    
    # 4.1 Steering Command (Pulse Width: 47 Hz, 1065us to 1959us)
    
    # Clip normalized action to the valid range [-1.0, 1.0]
    steer_clipped = np.clip(normalized_steer, -1.0, 1.0)
    
    # Formula: US_output = Neutral + (Clipped_Action * Range)
    # 1491 us + (Action * 450 us)
    steering_pulse_us = int(STEERING_NEUTRAL_US + (steer_clipped * STEERING_RANGE_US))
    
    # Inject 47 Hz PWM signal using pigpio's set_servo_pulsewidth
    # Note: pigpio uses set_servo_pulsewidth to generate PWM in the 50-400Hz range,
    # which is close enough to our target 47 Hz for the servo.
    pi.set_servo_pulsewidth(STEERING_PIN_GPIO, steering_pulse_us)
    
    
    # 4.2 Throttle Command (Duty Cycle: 985 Hz, 0% to 70%)
    
    # Clip normalized action to the valid range [0.0, 1.0]
    throttle_clipped = np.clip(normalized_throttle, 0.0, 1.0)
    
    # Formula: Duty_Percent = Clipped_Action * Max_Duty
    throttle_duty_percent = throttle_clipped * THROTTLE_MAX_DUTY
    
    # Convert % Duty to an integer Duty Cycle (pigpio uses 0-1,000,000 range for PWM duty)
    # Duty Cycle = Duty_Percent * 10000 
    throttle_duty_cycle = int(throttle_duty_percent * 10000)
    
    # Set the frequency and then the duty cycle for the ESC
    pi.set_PWM_frequency(THROTTLE_PIN_GPIO, 985) # Set to confirmed 985 Hz
    pi.set_PWM_dutycycle(THROTTLE_PIN_GPIO, throttle_duty_cycle)


def autonomous_control_example():
    """Main loop for running autonomous control (inference)."""
    
    model = MockACTPolicy()
    frame_counter = 0

    print(f"--- Starting Autonomous Control Loop at {CAMERA_FPS} Hz ---")
    print("RC Transmitter MUST BE OFF. Hit CTRL+C to stop.")

    try:
        while True:
            loop_start_time = time.time()
            frame_counter += 1
            
            # --- STEP 1: CAPTURE OBSERVATION (Needs separate script/integration) ---
            # NOTE: In a production system, this involves reading the 1080p 30fps stream
            # from your Innomaker camera.
            # Example: current_frame = camera.get_latest_frame()
            current_frame = np.zeros((1080, 1920, 3), dtype=np.uint8) # Mock image
            
            # --- STEP 2: ACT INFERENCE ---
            steer_action, throttle_action = model.predict_action(current_frame)
            
            # --- STEP 3: COMMAND INJECTION ---
            set_control_commands(steer_action, throttle_action)
            
            # Optional: Print status
            if frame_counter % 5 == 0:
                 print(f"Frame: {frame_counter} | Predicted STEER: {steer_action:.4f} | THROTTLE: {throttle_action:.4f}")

            # --- STEP 4: TIMING LOCK ---
            # Wait for the remaining time to maintain strict 30 Hz loop
            time_elapsed = time.time() - loop_start_time
            time_to_wait = CONTROL_INTERVAL - time_elapsed
            
            if time_to_wait > 0:
                 time.sleep(time_to_wait)
            else:
                 print(f"WARNING: Loop missed 30Hz deadline! ({time_elapsed*1000:.2f} ms)")

    except KeyboardInterrupt:
        print("\nAutonomous control stopped. Stopping motors...")
    except Exception as e:
        print(f"\nAn error occurred: {e}")
    finally:
        # Emergency Stop: Set both to neutral/zero output
        pi.set_servo_pulsewidth(STEERING_PIN_GPIO, 0)
        pi.set_PWM_dutycycle(THROTTLE_PIN_GPIO, 0)
        pi.stop()


if __name__ == '__main__':
    autonomous_control_example()
