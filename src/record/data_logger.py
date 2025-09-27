# -----------------------------------------------------------------------------
# ⚠️  DEPRECATED: DIRECT GPIO PWM READING APPROACH
# -----------------------------------------------------------------------------
# This script is DEPRECATED in favor of the Arduino-based approach.
# 
# Current recommended setup:
# - Arduino UNO R3 reads PWM signals on pins 2 & 3
# - Raspberry Pi receives data via USB serial
# - Use integrated_data_collector.py instead
#
# This file is kept for reference only.
# -----------------------------------------------------------------------------
#
# LEGACY ACT POLICY DATA LOGGER: FTX TRACER TRUGGY (Phase I)
# -----------------------------------------------------------------------------
# This script reads PWM signals from the RC car's integrated ESC/Receiver board
# and logs the normalized state-action pairs to a CSV file.
#
# Synchronization: Locked to 30 Hz (30 frames per second) to match the video.
# Hardware Required: Raspberry Pi 5, Logic Level Converter, RC Car Taps.
# Prerequisite: pigpiod daemon must be running ('sudo pigpiod').
# -----------------------------------------------------------------------------

import pigpio
import time
import csv
import os

# --- 1. HARDWARE CONFIGURATION ---

# BCM (GPIO) Pin assignments on the Raspberry Pi
# Connected via Level Converter:
STEERING_PIN_GPIO = 18  # BCM 18: Steering (PWM Servo tap)
THROTTLE_PIN_GPIO = 23  # BCM 23: Throttle (PWM Drive tap)

# Confirmed PWM Signal Parameters (DO NOT CHANGE)
STEERING_NEUTRAL_US = 1491
STEERING_RANGE_US = 450 
THROTTLE_MAX_DUTY = 70.0 

# --- SYNCHRONIZATION PARAMETERS ---
CAMERA_FPS = 30.0  # Innolmaker camera framerate
LOGGING_INTERVAL = 1.0 / CAMERA_FPS # Required time delay between logs (approx 0.0333 seconds)


# --- 2. PIGPIO INITIALIZATION & LOGGER SETUP ---
pi = pigpio.pi()
if not pi.connected:
    print("Error: Could not connect to pigpio daemon. Run 'sudo pigpiod'.")
    exit()

OUTPUT_FILENAME = f"teleop_data_{time.strftime('%Y%m%d_%H%M%S')}.csv"
FIELDNAMES = [
    'frame_id',                 # Frame counter for synchronizing with video file frames
    'timestamp',                # High-resolution timestamp for synchronization
    'steering_normalized',      # observation.state & teleop.command (Normalized -1.0 to 1.0)
    'throttle_normalized',      # observation.state & teleop.command (Normalized 0.0 to 1.0)
    'steering_raw_us',          # Raw data for debugging
    'throttle_raw_duty_percent' # Raw data for debugging
]

# --- 3. RC READER CLASS ---

class RCReader:
    """Accurately reads PWM pulse width and period using pigpio callbacks."""
    def __init__(self, pi_instance, pin, neutral_us):
        self.pi = pi_instance
        self.pin = pin
        self.neutral_us = neutral_us
        self.last_tick_rising = self.pi.get_current_tick()
        self.pulse_width = 0 
        self.period = 0      
        
        self.pi.set_mode(pin, pigpio.INPUT)
        self.cb = self.pi.callback(pin, pigpio.EITHER_EDGE, self._cb)

    def _cb(self, pin, level, tick):
        """Hardware callback function executed on every signal edge."""
        if level == 1: 
            self.period = pigpio.tickDiff(self.last_tick_rising, tick)
            self.last_tick_rising = tick
        
        elif level == 0: 
            self.pulse_width = pigpio.tickDiff(self.last_tick_rising, tick)
    
    def get_normalized_action(self):
        """Converts raw PWM data to a normalized action suitable for ML training."""
        
        if self.pin == STEERING_PIN_GPIO:
            # STEERING: Pulse Width (us) based, normalized -1.0 to 1.0
            if self.pulse_width < 10: return 0.0 
            
            normalized = (self.pulse_width - self.neutral_us) / STEERING_RANGE_US
            return max(-1.0, min(1.0, normalized))
        
        elif self.pin == THROTTLE_PIN_GPIO:
            # THROTTLE: Duty Cycle (%) based, normalized 0.0 to 1.0
            if self.pulse_width < 10 or self.period < 10: 
                return 0.0
            
            duty_cycle_percent = (self.pulse_width / self.period) * 100
            
            normalized = duty_cycle_percent / THROTTLE_MAX_DUTY
            return max(0.0, min(1.0, normalized))

        return 0.0

    def get_raw_data(self):
        """Returns raw measurement data for debugging/logging."""
        if self.pin == STEERING_PIN_GPIO:
            return self.pulse_width 
        elif self.pin == THROTTLE_PIN_GPIO:
            # Return Duty Cycle %
            if self.period > 0:
                 return (self.pulse_width / self.period) * 100
            return 0.0
        return 0.0

    def cancel(self):
        self.cb.cancel()

# --- 4. MAIN LOGGING FUNCTION ---

def start_data_logging():
    """Main loop for logging expert commands to a CSV file."""
    
    # Initialize readers for both channels
    steering_reader = RCReader(pi, STEERING_PIN_GPIO, STEERING_NEUTRAL_US)
    throttle_reader = RCReader(pi, THROTTLE_PIN_GPIO, STEERING_NEUTRAL_US)
    
    frame_counter = 0

    print(f"--- Starting Data Logging to: {OUTPUT_FILENAME} ---")
    print(f"Logging actions locked at {CAMERA_FPS:.1f} Hz. RC Transmitter ON. Hit CTRL+C to stop.")
    print(f"Logging interval: {LOGGING_INTERVAL*1000:.2f} ms")


    try:
        with open(OUTPUT_FILENAME, 'w', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=FIELDNAMES)
            writer.writeheader()
            
            
            while True:
                loop_start_time = time.time()
                
                # 1. Read Actions and Timestamp
                current_time = loop_start_time
                steer_action = steering_reader.get_normalized_action()
                throttle_action = throttle_reader.get_normalized_action()
                
                # 2. Increment Frame ID and Write Data
                frame_counter += 1
                
                # NOTE: This frame_id should be used to name or index your video frames 
                # for perfect synchronization during ML preprocessing.
                
                row = {
                    'frame_id': frame_counter,
                    'timestamp': current_time,
                    'steering_normalized': steer_action,
                    'throttle_normalized': throttle_action,
                    'steering_raw_us': steering_reader.pulse_width,
                    'throttle_raw_duty_percent': throttle_reader.get_raw_data()
                }
                writer.writerow(row)
                
                # Optional: Print status to console (can be removed for high-speed logging)
                if frame_counter % 5 == 0:
                     print(f"Frame: {frame_counter} | STEER: {steer_action:.4f} | THROTTLE: {throttle_action:.4f}")
                
                # 3. Control Loop Timing
                # Calculate remaining time needed for the loop to complete at 30 Hz
                time_elapsed = time.time() - loop_start_time
                time_to_wait = LOGGING_INTERVAL - time_elapsed
                
                if time_to_wait > 0:
                     time.sleep(time_to_wait) 
                
    except KeyboardInterrupt:
        print("\nLogging complete. Closing file and cleaning up GPIO.")
    except Exception as e:
        print(f"\nAn error occurred: {e}")
    finally:
        steering_reader.cancel()
        throttle_reader.cancel()
        # Clean up the GPIO pins
        pi.stop()

if __name__ == '__main__':
    start_data_logging()
