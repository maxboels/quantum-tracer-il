#!/usr/bin/env python3
"""
Comprehensive diagnostic script for RC PWM signal debugging
"""
import lgpio
import time
import threading

# Pin configuration
PINS_TO_TEST = [18, 23]  # Steering and Throttle
PIN_NAMES = ["Steering", "Throttle"]

# Global variables for edge detection
edge_counts = {pin: 0 for pin in PINS_TO_TEST}
last_edge_time = {pin: 0 for pin in PINS_TO_TEST}
signal_detected = {pin: False for pin in PINS_TO_TEST}

def edge_callback(chip, gpio, level, tick):
    """Callback for any edge detection"""
    global edge_counts, last_edge_time, signal_detected
    edge_counts[gpio] += 1
    last_edge_time[gpio] = time.time()
    signal_detected[gpio] = True

def main():
    print("=== RC PWM Signal Diagnostic Tool ===")
    print("This tool will help identify issues with PWM signal detection\n")
    
    # Initialize lgpio
    try:
        h = lgpio.gpiochip_open(0)
        print("✓ Successfully opened GPIO chip")
    except Exception as e:
        print(f"✗ Failed to open GPIO chip: {e}")
        return
    
    # Setup pins and callbacks
    callbacks = {}
    try:
        for i, pin in enumerate(PINS_TO_TEST):
            # Claim pin as input
            lgpio.gpio_claim_input(h, pin)
            print(f"✓ Claimed GPIO {pin} ({PIN_NAMES[i]}) as input")
            
            # Setup callback for edge detection
            callbacks[pin] = lgpio.callback(h, pin, lgpio.BOTH_EDGES, edge_callback)
            print(f"✓ Setup edge detection for GPIO {pin}")
    
    except Exception as e:
        print(f"✗ Error setting up pins: {e}")
        lgpio.gpiochip_close(h)
        return
    
    print("\n=== Starting Diagnostics ===")
    print("1. Testing basic GPIO reads...")
    print("2. Monitoring for PWM signals...")
    print("3. Press CTRL+C to stop\n")
    
    try:
        start_time = time.time()
        last_report = time.time()
        
        while True:
            current_time = time.time()
            
            # Read current pin states
            pin_states = {}
            for pin in PINS_TO_TEST:
                try:
                    pin_states[pin] = lgpio.gpio_read(h, pin)
                except Exception as e:
                    pin_states[pin] = f"ERROR: {e}"
            
            # Print current status every 2 seconds
            if current_time - last_report >= 2.0:
                print(f"\n--- Status Report (Runtime: {current_time - start_time:.1f}s) ---")
                
                for i, pin in enumerate(PINS_TO_TEST):
                    state = pin_states[pin]
                    edges = edge_counts[pin]
                    last_edge = last_edge_time[pin]
                    time_since_edge = current_time - last_edge if last_edge > 0 else 0
                    detected = "YES" if signal_detected[pin] else "NO"
                    
                    print(f"{PIN_NAMES[i]:8} (Pin {pin:2d}): State={state} | Edges={edges:4d} | Signal={detected:3s} | Last Edge: {time_since_edge:.1f}s ago")
                
                last_report = current_time
            
            time.sleep(0.1)
    
    except KeyboardInterrupt:
        print("\n\n=== Diagnostic Summary ===")
        runtime = time.time() - start_time
        
        for i, pin in enumerate(PINS_TO_TEST):
            edges = edge_counts[pin]
            detected = signal_detected[pin]
            
            print(f"{PIN_NAMES[i]} (GPIO {pin}):")
            print(f"  - Total edges detected: {edges}")
            print(f"  - Signal present: {'YES' if detected else 'NO'}")
            
            if edges > 0:
                avg_freq = edges / (2 * runtime)  # Divide by 2 since we count both rising and falling
                print(f"  - Average frequency: {avg_freq:.1f} Hz")
            else:
                print(f"  - No PWM signal detected")
            print()
        
        print("Troubleshooting suggestions:")
        if not any(signal_detected.values()):
            print("- Check that your RC transmitter is ON and paired with the receiver")
            print("- Verify wiring connections (especially ground connections)")
            print("- Check that the logic level converter is powered and working")
            print("- Verify you're tapping the correct points on the RC receiver board")
            print("- Try different GPIO pins in case of pin damage")
        else:
            print("- Some signals detected! Check individual pin connections for non-working channels")
    
    finally:
        # Cleanup
        print("\nCleaning up...")
        for pin, cb in callbacks.items():
            try:
                cb.cancel()
                lgpio.gpio_free(h, pin)
            except:
                pass
        
        lgpio.gpiochip_close(h)
        print("Cleanup complete.")

if __name__ == "__main__":
    main()