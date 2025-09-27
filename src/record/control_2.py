# ⚠️ DEPRECATED: This script uses direct GPIO PWM reading
# Current setup uses Arduino-based PWM reading instead
# Use integrated_data_collector.py for data recording

import RPi.GPIO as GPIO
import time

PIN = 23
GPIO.setmode(GPIO.BCM)
GPIO.setup(PIN, GPIO.IN)

last_rise = None
period = None
high_time = None

def edge_callback(channel):
    global last_rise, period, high_time
    current_time = time.time()
    current_level = GPIO.input(channel)
    
    if current_level == 1:  # Rising edge
        if last_rise is not None:
            period = current_time - last_rise
        last_rise = current_time
    else:  # Falling edge
        if last_rise is not None:
            high_time = current_time - last_rise

# Set up interrupt for both edges
GPIO.add_event_detect(PIN, GPIO.BOTH, callback=edge_callback, bouncetime=1)

try:
    print("Monitoring PWM signal on pin", PIN)
    print("Press Ctrl+C to stop...")
    print("Waiting for signal... Move the car controls to see values!")
    print("-" * 50)
    
    while True:
        if period and high_time and period > 0:
            freq = 1.0 / period
            duty = (high_time / period) * 100.0
            print(f"Signal detected: f={freq:.1f} Hz, duty={duty:.2f}% | Period={period*1000:.1f}ms, High={high_time*1000:.1f}ms")
            period = high_time = None
        else:
            # Show current pin state even when no complete signal
            current_state = GPIO.input(PIN)
            print(f"Pin {PIN} state: {'HIGH' if current_state else 'LOW'} | Waiting for complete PWM cycle...", end='\r')
        time.sleep(0.1)
except KeyboardInterrupt:
    print("\nStopping...")
finally:
    GPIO.cleanup()