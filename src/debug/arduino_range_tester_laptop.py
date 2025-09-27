#!/usr/bin/env python3
"""
Arduino PWM Range Tester - Laptop Version
=========================================
Records Arduino PWM data to find min/max ranges for calibration.
Run this on your laptop while Arduino is connected via USB.

Requirements:
    pip install pyserial

Usage:
    python arduino_range_tester_laptop.py --port COM3 --duration 30
    (On Windows, use COM3, COM4, etc.)
    (On Mac/Linux, use /dev/ttyUSB0, /dev/ttyACM0, etc.)
"""

import serial
import time
import argparse
import sys
import platform

class PWMRangeTester:
    def __init__(self, port=None, baudrate=115200):
        self.port = port or self._detect_port()
        self.baudrate = baudrate
        self.serial_conn = None
        
        # Data storage
        self.steering_values = []
        self.throttle_values = []
        self.steering_raw = []
        self.throttle_raw = []
        
    def _detect_port(self):
        """Try to detect Arduino port automatically"""
        import serial.tools.list_ports
        
        arduino_ports = []
        for port in serial.tools.list_ports.comports():
            if 'Arduino' in port.description or 'CH340' in port.description or 'USB' in port.description:
                arduino_ports.append(port.device)
                
        if arduino_ports:
            print(f"🔍 Found potential Arduino ports: {arduino_ports}")
            return arduino_ports[0]
        
        # Default guesses
        if platform.system() == 'Windows':
            return 'COM3'
        else:
            return '/dev/ttyUSB0'
            
    def connect(self):
        """Connect to Arduino"""
        try:
            print(f"🔌 Connecting to Arduino on {self.port}...")
            self.serial_conn = serial.Serial(self.port, self.baudrate, timeout=1)
            time.sleep(2)  # Wait for Arduino reset
            
            # Wait for ARDUINO_READY
            timeout = 10
            start = time.time()
            while time.time() - start < timeout:
                line = self.serial_conn.readline().decode('utf-8', errors='ignore').strip()
                if line == "ARDUINO_READY":
                    print("✅ Arduino connected and ready!")
                    return True
                elif line:
                    print(f"⏳ Waiting... got: {line[:50]}")
                    
            print("❌ Timeout waiting for Arduino ready signal")
            return False
                    
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            print("💡 Try different port or check if Arduino IDE Serial Monitor is closed")
            return False
    
    def record_data(self, duration=30):
        """Record PWM data for specified duration"""
        if not self.serial_conn:
            print("❌ Not connected to Arduino")
            return
            
        print(f"\n🎬 Starting {duration} second recording...")
        print("📋 INSTRUCTIONS:")
        print("   1. Turn ON your RC transmitter")
        print("   2. Move STEERING through full range: Left → Center → Right")
        print("   3. Move THROTTLE through full range: Brake → Neutral → Full")
        print("   4. Repeat multiple times for good data")
        print("=" * 60)
        
        input("Press ENTER when ready to start recording...")
        
        start_time = time.time()
        sample_count = 0
        last_report = 0
        
        while (time.time() - start_time) < duration:
            try:
                line = self.serial_conn.readline().decode('utf-8', errors='ignore').strip()
                
                if line.startswith("DATA,"):
                    self.parse_and_store(line)
                    sample_count += 1
                    
                    # Progress report every 3 seconds
                    elapsed = time.time() - start_time
                    if elapsed - last_report >= 3:
                        remaining = duration - elapsed
                        print(f"⏱️  {elapsed:.0f}s elapsed, {remaining:.0f}s remaining")
                        self.print_current_ranges()
                        print("   (Keep moving controls!)")
                        last_report = elapsed
                        
            except KeyboardInterrupt:
                print("\n⏹️  Recording stopped by user")
                break
            except Exception as e:
                print(f"⚠️  Error: {e}")
                
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
                
                # Store all values (including zeros for analysis)
                self.steering_values.append(steering_norm)
                self.throttle_values.append(throttle_norm)
                if steer_raw > 0:
                    self.steering_raw.append(steer_raw)
                if throttle_raw > 0:
                    self.throttle_raw.append(throttle_raw)
                    
        except (ValueError, IndexError):
            pass  # Skip malformed lines
    
    def print_current_ranges(self):
        """Print current min/max ranges"""
        if self.steering_raw:
            steer_norm_min = min([v for v in self.steering_values if v != 0])
            steer_norm_max = max([v for v in self.steering_values if v != 0])
            steer_raw_min, steer_raw_max = min(self.steering_raw), max(self.steering_raw)
            print(f"   🎯 Steering: {steer_norm_min:.3f} to {steer_norm_max:.3f} (raw: {steer_raw_min}-{steer_raw_max}µs)")
        else:
            print("   🎯 Steering: No signal detected - check Pin 2 connection")
            
        if self.throttle_raw:
            throttle_norm_min = min([v for v in self.throttle_values if v != 0])
            throttle_norm_max = max([v for v in self.throttle_values if v != 0])
            throttle_raw_min, throttle_raw_max = min(self.throttle_raw), max(self.throttle_raw)
            print(f"   🚗 Throttle: {throttle_norm_min:.3f} to {throttle_norm_max:.3f} (raw: {throttle_raw_min}-{throttle_raw_max}µs)")
        else:
            print("   🚗 Throttle: No signal detected - check Pin 3 connection")
    
    def analyze_and_report(self):
        """Analyze collected data and provide calibration recommendations"""
        print("\n" + "="*70)
        print("📊 CALIBRATION ANALYSIS RESULTS")
        print("="*70)
        
        if not self.steering_raw and not self.throttle_raw:
            print("❌ NO PWM SIGNALS DETECTED!")
            print("\n🔧 TROUBLESHOOTING:")
            print("   1. Is RC transmitter turned ON?")
            print("   2. Are PWM wires connected to Arduino pins 2 and 3?")
            print("   3. Check wire connections (signal, ground)")
            print("   4. Verify receiver is bound to transmitter")
            return
            
        # Steering Analysis
        if self.steering_raw:
            non_zero_steering = [v for v in self.steering_values if v != 0]
            steer_min = min(non_zero_steering)
            steer_max = max(non_zero_steering)
            steer_raw_min = min(self.steering_raw)
            steer_raw_max = max(self.steering_raw)
            steer_center = (steer_raw_min + steer_raw_max) // 2
            steer_range = (steer_raw_max - steer_raw_min) // 2
            
            print(f"\n🎯 STEERING CHANNEL RESULTS:")
            print(f"   📏 Normalized Range: {steer_min:.4f} to {steer_max:.4f}")
            print(f"   📐 Raw Pulse Width: {steer_raw_min}µs to {steer_raw_max}µs")
            print(f"   🎚️  Total Range: {steer_raw_max - steer_raw_min}µs")
            print(f"\n   🔧 SUGGESTED ARDUINO CODE UPDATES:")
            print(f"      const unsigned long STEERING_NEUTRAL_US = {steer_center};")
            print(f"      const unsigned long STEERING_RANGE_US = {steer_range};")
            
            # Quality check
            if (steer_raw_max - steer_raw_min) > 800:
                print("   ✅ Excellent range - good for precise control")
            elif (steer_raw_max - steer_raw_min) > 400:
                print("   ✅ Good range - adequate for training")
            else:
                print("   ⚠️  Limited range - consider adjusting transmitter endpoints")
        else:
            print(f"\n🎯 STEERING: ❌ No signal on Pin 2")
        
        # Throttle Analysis  
        if self.throttle_raw:
            non_zero_throttle = [v for v in self.throttle_values if v != 0]
            throttle_min = min(non_zero_throttle)
            throttle_max = max(non_zero_throttle)
            throttle_raw_min = min(self.throttle_raw)
            throttle_raw_max = max(self.throttle_raw)
            
            print(f"\n🚗 THROTTLE CHANNEL RESULTS:")
            print(f"   📏 Normalized Range: {throttle_min:.4f} to {throttle_max:.4f}")
            print(f"   📐 Raw Pulse Width: {throttle_raw_min}µs to {throttle_raw_max}µs")
            print(f"   🎚️  Total Range: {throttle_raw_max - throttle_raw_min}µs")
            
            # Estimate new calibration
            period_est = 20000  # ~20ms period assumption
            duty_max = (throttle_raw_max / period_est) * 100
            
            print(f"\n   🔧 SUGGESTED ARDUINO CODE UPDATES:")
            print(f"      const float THROTTLE_MAX_DUTY = {duty_max:.1f};")
            
            # Quality check
            if throttle_max > 0.7:
                print("   ✅ Good throttle range")
            else:
                print("   ⚠️  Limited throttle range - check transmitter settings")
        else:
            print(f"\n🚗 THROTTLE: ❌ No signal on Pin 3")
            
        print(f"\n📊 SUMMARY:")
        print(f"   Total samples collected: {len(self.steering_values)}")
        print(f"   Steering samples with signal: {len(self.steering_raw)}")
        print(f"   Throttle samples with signal: {len(self.throttle_raw)}")
        
    def close(self):
        """Close serial connection"""
        if self.serial_conn:
            self.serial_conn.close()

def main():
    parser = argparse.ArgumentParser(description='Arduino PWM Range Tester (Laptop Version)')
    parser.add_argument('--port', type=str, help='Arduino serial port (e.g., COM3, /dev/ttyUSB0)')
    parser.add_argument('--duration', type=int, default=30, help='Recording duration in seconds')
    
    args = parser.parse_args()
    
    print("🔧 Arduino PWM Range Tester (Laptop Version)")
    print("=" * 50)
    
    # Try to install pyserial if not available
    try:
        import serial.tools.list_ports
    except ImportError:
        print("❌ pyserial not found. Install with: pip install pyserial")
        sys.exit(1)
    
    tester = PWMRangeTester(args.port)
    
    try:
        if tester.connect():
            tester.record_data(args.duration)
            tester.analyze_and_report()
        else:
            print("\n💡 TIPS:")
            print("   • Close Arduino IDE Serial Monitor if open")
            print("   • Try different port with --port COM4 (Windows) or --port /dev/ttyUSB1 (Linux)")
            print("   • Check USB cable connection")
            
    except KeyboardInterrupt:
        print("\n\n👋 Test interrupted")
    finally:
        tester.close()

if __name__ == '__main__':
    main()