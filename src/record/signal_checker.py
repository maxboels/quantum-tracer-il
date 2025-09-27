# ⚠️ DEPRECATED: This script uses direct GPIO PWM reading
# Current setup uses Arduino-based PWM reading instead
# Arduino reads PWM on pins 2&3, sends via USB serial to Raspberry Pi

import lgpio
import time

# --- HARDWARE CONFIGURATION (DEPRECATED) ---
# BCM (GPIO) Pin assignments on the Raspberry Pi
STEERING_PIN_GPIO = 18  # BCM 18: Steering (PWM Servo tap)
THROTTLE_PIN_GPIO = 23  # BCM 23: Throttle (PWM Drive tap)

# --- LGPIO INITIALIZATION ---
try:
    # Open the default GPIO chip
    h = lgpio.gpiochip_open(0)
except lgpio.error as e:
    print(f"Error opening GPIO chip: {e}")
    exit()

# --- CLAIM PINS AS INPUT ---
try:
    # Claim the GPIO pins for input
    lgpio.gpio_claim_input(h, STEERING_PIN_GPIO)
    lgpio.gpio_claim_input(h, THROTTLE_PIN_GPIO)
    print(f"Successfully claimed GPIO {STEERING_PIN_GPIO} and {THROTTLE_PIN_GPIO} as inputs.")
except lgpio.error as e:
    print(f"Error claiming GPIO pins: {e}")
    lgpio.gpiochip_close(h)
    exit()

print("\n--- Starting GPIO Read Loop ---")
print("This script reads the raw digital state (1 for HIGH, 0 for LOW).")
print("Move your transmitter controls to see if the values change.")
print("Hit CTRL+C to stop.\n")

try:
    while True:
        # Read the digital level of the GPIO pins
        steer_level = lgpio.gpio_read(h, STEERING_PIN_GPIO)
        throttle_level = lgpio.gpio_read(h, THROTTLE_PIN_GPIO)

        print(f"\rTimestamp: {time.time():.2f} | Steering (Pin {STEERING_PIN_GPIO}): {steer_level} | Throttle (Pin {THROTTLE_PIN_GPIO}): {throttle_level}", end="")

        # Sleep for a short duration to make the output readable
        time.sleep(0.05)

except KeyboardInterrupt:
    print("\n\n--- Loop stopped by user ---")

finally:
    # --- CLEANUP ---
    print("Releasing GPIO pins and closing chip handle.")
    # Free the GPIO pins
    lgpio.gpio_free(h, STEERING_PIN_GPIO)
    lgpio.gpio_free(h, THROTTLE_PIN_GPIO)
    # Close the GPIO chip handle
    lgpio.gpiochip_close(h)
    print("Cleanup complete.")
