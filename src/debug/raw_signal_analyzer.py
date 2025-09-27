#!/usr/bin/env python3
"""
Raw PWM Signal Analyzer
========================
Captures raw PWM timing data from Arduino to analyze signal characteristics
and identify optimal filtering parameters.
"""

import serial
import time
import sys

def analyze_raw_signals(port='/dev/ttyACM0', duration=15):
    """Capture and analyze raw PWM signals"""
    
    print("📡 Raw PWM Signal Analysis")
    print("Move your RC controls through full range...")
    print("=" * 50)
    
    try:
        ser = serial.Serial(port, 115200, timeout=1)
        time.sleep(2)
        
        throttle_data = []
        steering_data = []
        
        start_time = time.time()
        
        while time.time() - start_time < duration:
            try:
                line = ser.readline().decode('utf-8').strip()
                if line.startswith('DATA,'):
                    parts = line.split(',')
                    if len(parts) >= 8:
                        steer_raw = int(parts[4])
                        throttle_raw = int(parts[5])
                        steer_period = int(parts[6])
                        throttle_period = int(parts[7])
                        
                        if steer_raw > 0:
                            steering_data.append((steer_raw, steer_period))
                        if throttle_raw > 0:
                            throttle_data.append((throttle_raw, throttle_period))
                            
                        # Real-time display
                        print(f"\rSteer: {steer_raw:4d}µs/{steer_period:5d}µs | Throttle: {throttle_raw:4d}µs/{throttle_period:5d}µs", end="")
                        
            except Exception as e:
                continue
                
        ser.close()
        
        # Analysis
        print(f"\n\n📊 Signal Analysis Results:")
        print(f"Duration: {duration}s")
        
        if steering_data:
            steer_pulses = [x[0] for x in steering_data]
            steer_periods = [x[1] for x in steering_data]
            print(f"\n🎯 STEERING:")
            print(f"   Samples: {len(steering_data)}")
            print(f"   Pulse width: {min(steer_pulses)}µs to {max(steer_pulses)}µs")
            print(f"   Period: {min(steer_periods)}µs to {max(steer_periods)}µs")
            print(f"   Frequency: ~{1000000/statistics.mean(steer_periods):.1f}Hz" if steer_periods else "")
        
        if throttle_data:
            throttle_pulses = [x[0] for x in throttle_data]
            throttle_periods = [x[1] for x in throttle_data]
            print(f"\n🚗 THROTTLE:")
            print(f"   Samples: {len(throttle_data)}")
            print(f"   Pulse width: {min(throttle_pulses)}µs to {max(throttle_periods)}µs")
            print(f"   Period: {min(throttle_periods)}µs to {max(throttle_periods)}µs")
            print(f"   Frequency: ~{1000000/statistics.mean(throttle_periods):.1f}Hz" if throttle_periods else "")
            
            # Duty cycle analysis
            duty_cycles = [(p[0]/p[1])*100 for p in throttle_data if p[1] > 0]
            if duty_cycles:
                print(f"   Duty cycle: {min(duty_cycles):.2f}% to {max(duty_cycles):.2f}%")
        
        # Recommendations for Arduino code
        print(f"\n🔧 Arduino Code Recommendations:")
        
        if throttle_data:
            min_throttle_period = min([x[1] for x in throttle_data])
            if min_throttle_period < 500:
                print(f"   ⚠️  Throttle period filter too restrictive!")
                print(f"       Current: period >= 500µs")
                print(f"       Detected: {min_throttle_period}µs minimum")
                print(f"       Suggest: period >= {max(100, min_throttle_period//2)}µs")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    import statistics
    analyze_raw_signals(duration=15)