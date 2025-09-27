#!/usr/bin/env python3
"""
Arduino PWM Range Tester
========================
Records Arduino PWM data to find min/max ranges for steering and throttle calibration.

Usage:
    python3 arduino_range_tester.py --port /dev/ttyUSB0 --duration 60
"""

import serial
import time
import argparse
import sys
from collections import defaultdict

class PWMRangeTester:
    def __init__(self, port='/dev/ttyUSB0', baudrate=115200):
        self.port = port
        self.baudrate = baudrate
        self.serial_conn = None
        
        # Data storage
        self.steering_values = []
        self.throttle_values = []
        self.steering_raw = []
        self.throttle_raw = []
        
    def connect(self):
        """Connect to Arduino"""
        try:
            print(f"Connecting to Arduino on {self.port}...")
            self.serial_conn = serial.Serial(self.port, self.baudrate, timeout=1)
            time.sleep(2)  # Wait for Arduino reset
            
            # Wait for ARDUINO_READY
            while True:
                line = self.serial_conn.readline().decode('utf-8', errors='ignore').strip()
                if line == "ARDUINO_READY":
                    print("✅ Arduino connected and ready!")
                    return True
                elif line:
                    print(f"Waiting for Arduino ready... got: {line}")
                    
        except Exception as e:
            print(f"❌ Failed to connect: {e}")
            return False
    
    def record_data(self, duration=60):
        """Record PWM data for specified duration"""
        if not self.serial_conn:
            print("❌ Not connected to Arduino")
            return
            
        print(f"\n🎬 Starting {duration} second recording...")
        print("📋 Move steering and throttle through their FULL RANGE")
        print("   - Steering: Full left → Center → Full right")
        print("   - Throttle: Full brake → Neutral → Full throttle")
        print("=" * 60)
        
        start_time = time.time()
        sample_count = 0
        last_report = 0
        
        while (time.time() - start_time) < duration:
            try:
                line = self.serial_conn.readline().decode('utf-8', errors='ignore').strip()
                
                if line.startswith("DATA,"):
                    self.parse_and_store(line)
                    sample_count += 1
                    
                    # Progress report every 5 seconds
                    elapsed = time.time() - start_time
                    if elapsed - last_report >= 5:
                        remaining = duration - elapsed
                        print(f"⏱️  {elapsed:.0f}s elapsed, {remaining:.0f}s remaining, {sample_count} samples")
                        self.print_current_ranges()
                        last_report = elapsed
                        
            except KeyboardInterrupt:
                print("\n⏹️  Recording stopped by user")
                break
            except Exception as e:
                print(f"⚠️  Error reading data: {e}")
                
        print(f"\n✅ Recording complete! Collected {sample_count} samples")
        
    def parse_and_store(self, line):
        """Parse DATA line and store values"""
        try:
            # DATA,timestamp,steering_norm,throttle_norm,steer_raw,throttle_raw,steer_period,throttle_period
            parts = line.split(',')
            if len(parts) >= 7:
                steering_norm = float(parts[2])
                throttle_norm = float(parts[3])
                steer_raw = int(parts[4]) if parts[4] != '0' else 0
                throttle_raw = int(parts[5]) if parts[5] != '0' else 0
                
                # Only store non-zero values (actual signals)
                if steer_raw > 0:
                    self.steering_values.append(steering_norm)
                    self.steering_raw.append(steer_raw)
                if throttle_raw > 0:
                    self.throttle_values.append(throttle_norm)
                    self.throttle_raw.append(throttle_raw)
                    
        except (ValueError, IndexError) as e:
            pass  # Skip malformed lines
    
    def print_current_ranges(self):
        """Print current min/max ranges"""
        if self.steering_values:
            steer_min, steer_max = min(self.steering_values), max(self.steering_values)
            steer_raw_min, steer_raw_max = min(self.steering_raw), max(self.steering_raw)
            print(f"   🎯 Steering: {steer_min:.3f} to {steer_max:.3f} (raw: {steer_raw_min}-{steer_raw_max}µs)")
        else:
            print("   🎯 Steering: No signal detected")
            
        if self.throttle_values:
            throttle_min, throttle_max = min(self.throttle_values), max(self.throttle_values)
            throttle_raw_min, throttle_raw_max = min(self.throttle_raw), max(self.throttle_raw)
            print(f"   🚗 Throttle: {throttle_min:.3f} to {throttle_max:.3f} (raw: {throttle_raw_min}-{throttle_raw_max}µs)")
        else:
            print("   🚗 Throttle: No signal detected")
    
    def analyze_and_report(self):
        """Analyze collected data and provide calibration recommendations"""
        print("\n" + "="*60)
        print("📊 FINAL ANALYSIS & CALIBRATION RECOMMENDATIONS")
        print("="*60)
        
        if not self.steering_values and not self.throttle_values:
            print("❌ NO DATA COLLECTED!")
            print("   Check that:")
            print("   • RC transmitter is turned on")
            print("   • PWM wires are connected to pins 2 and 3")
            print("   • Wiring connections are secure")
            return
            
        # Steering Analysis
        if self.steering_values:
            steer_min = min(self.steering_values)
            steer_max = max(self.steering_values)
            steer_raw_min = min(self.steering_raw)
            steer_raw_max = max(self.steering_raw)
            steer_center = (steer_raw_min + steer_raw_max) // 2
            steer_range = (steer_raw_max - steer_raw_min) // 2
            
            print(f"\n🎯 STEERING RESULTS:")
            print(f"   Normalized Range: {steer_min:.4f} to {steer_max:.4f}")
            print(f"   Raw Range: {steer_raw_min}µs to {steer_raw_max}µs")
            print(f"   Suggested Calibration:")
            print(f"     STEERING_NEUTRAL_US = {steer_center}")
            print(f"     STEERING_RANGE_US = {steer_range}")
            
            # Quality assessment
            if abs(steer_max - abs(steer_min)) < 0.1:
                print("   ✅ Good symmetric range")
            else:
                print("   ⚠️  Asymmetric range - check transmitter trims")
        else:
            print(f"\n🎯 STEERING: ❌ No signal detected on Pin 2")
        
        # Throttle Analysis  
        if self.throttle_values:
            throttle_min = min(self.throttle_values)
            throttle_max = max(self.throttle_values)
            throttle_raw_min = min(self.throttle_raw)
            throttle_raw_max = max(self.throttle_raw)
            
            print(f"\n🚗 THROTTLE RESULTS:")
            print(f"   Normalized Range: {throttle_min:.4f} to {throttle_max:.4f}")
            print(f"   Raw Range: {throttle_raw_min}µs to {throttle_raw_max}µs")
            
            # Estimate duty cycle range
            # Assuming ~20ms period (50Hz)
            period_estimate = 20000  # 20ms in microseconds
            duty_min = (throttle_raw_min / period_estimate) * 100
            duty_max = (throttle_raw_max / period_estimate) * 100
            
            print(f"   Estimated Duty Cycle: {duty_min:.1f}% to {duty_max:.1f}%")
            print(f"   Suggested Calibration:")
            print(f"     THROTTLE_MAX_DUTY = {duty_max:.1f}")
            
            # Quality assessment
            if throttle_max > 0.8:
                print("   ✅ Good throttle range")
            else:
                print("   ⚠️  Limited throttle range - check transmitter endpoints")
        else:
            print(f"\n🚗 THROTTLE: ❌ No signal detected on Pin 3")
            
        print(f"\n📈 Total Samples: {len(self.steering_values + self.throttle_values)}")
        
    def close(self):
        """Close serial connection"""
        if self.serial_conn:
            self.serial_conn.close()

def main():
    parser = argparse.ArgumentParser(description='Arduino PWM Range Tester')
    parser.add_argument('--port', type=str, default='/dev/ttyUSB0', help='Arduino serial port')
    parser.add_argument('--duration', type=int, default=60, help='Recording duration in seconds')
    parser.add_argument('--baudrate', type=int, default=115200, help='Serial baudrate')
    
    args = parser.parse_args()
    
    print("🔧 Arduino PWM Range Tester")
    print(f"Port: {args.port}")
    print(f"Duration: {args.duration} seconds")
    
    tester = PWMRangeTester(args.port, args.baudrate)
    
    try:
        if tester.connect():
            tester.record_data(args.duration)
            tester.analyze_and_report()
        else:
            print("Failed to connect to Arduino")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n\n👋 Test interrupted by user")
    finally:
        tester.close()

if __name__ == '__main__':
    main()