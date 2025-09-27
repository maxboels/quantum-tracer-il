#!/usr/bin/env python3
"""
Interactive PWM Calibration Tool
================================
Finds precise min/max values for throttle and steering channels.

This tool guides you through calibrating your RC car's control ranges
by having you move the controls to specific positions and recording the values.

Usage:
    python3 interactive_calibration.py --port /dev/ttyACM0
"""

import serial
import time
import argparse
import statistics
from collections import deque

class InteractiveCalibrator:
    def __init__(self, port='/dev/ttyACM0', baudrate=115200):
        self.port = port
        self.baudrate = baudrate
        self.serial_conn = None
        
        # Calibration data storage
        self.calibration_data = {
            'throttle_min': [],
            'throttle_max': [],
            'throttle_neutral': [],
            'steering_left': [],
            'steering_right': [],
            'steering_center': []
        }
        
    def connect(self):
        """Connect to Arduino"""
        try:
            print(f"🔌 Connecting to Arduino on {self.port}...")
            self.serial_conn = serial.Serial(self.port, self.baudrate, timeout=1)
            time.sleep(2)
            
            # Wait for ARDUINO_READY
            timeout = 10
            start = time.time()
            while time.time() - start < timeout:
                line = self.serial_conn.readline().decode('utf-8', errors='ignore').strip()
                if line == "ARDUINO_READY":
                    print("✅ Arduino connected and ready!")
                    return True
                elif line.startswith("DATA,"):
                    print("✅ Arduino already running, ready for calibration!")
                    return True
                    
            print("❌ Timeout waiting for Arduino")
            return False
            
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            return False
    
    def read_current_values(self, samples=10):
        """Read current PWM values and return averages"""
        throttle_raw = []
        steering_raw = []
        throttle_duty = []
        steering_duty = []
        
        print(f"   📊 Reading {samples} samples...", end="", flush=True)
        
        sample_count = 0
        while sample_count < samples:
            try:
                line = self.serial_conn.readline().decode('utf-8', errors='ignore').strip()
                if line.startswith("DATA,"):
                    parts = line.split(',')
                    if len(parts) >= 8:
                        # DATA,timestamp,steer_norm,throttle_norm,steer_raw,throttle_raw,steer_period,throttle_period
                        steer_raw = int(parts[4]) if parts[4] != '0' else 0
                        throttle_raw_val = int(parts[5]) if parts[5] != '0' else 0
                        steer_period = int(parts[6]) if parts[6] != '0' else 0
                        throttle_period = int(parts[7]) if parts[7] != '0' else 0
                        
                        # Calculate duty cycles
                        if throttle_raw_val > 0 and throttle_period > 0:
                            throttle_duty_val = (throttle_raw_val / throttle_period) * 100.0
                            throttle_raw.append(throttle_raw_val)
                            throttle_duty.append(throttle_duty_val)
                            
                        if steer_raw > 0 and steer_period > 0:
                            steer_duty_val = (steer_raw / steer_period) * 100.0
                            steering_raw.append(steer_raw)
                            steering_duty.append(steer_duty_val)
                            
                        sample_count += 1
                        print(".", end="", flush=True)
                        
            except (ValueError, IndexError):
                pass
                
        print(" Done!")
        
        # Return averages
        result = {}
        if throttle_duty:
            result['throttle_duty'] = statistics.mean(throttle_duty)
            result['throttle_raw'] = statistics.mean(throttle_raw)
        else:
            result['throttle_duty'] = 0
            result['throttle_raw'] = 0
            
        if steering_duty:
            result['steering_duty'] = statistics.mean(steering_duty)
            result['steering_raw'] = statistics.mean(steering_raw)
        else:
            result['steering_duty'] = 0
            result['steering_raw'] = 0
            
        return result
    
    def calibrate_position(self, position_name, instruction):
        """Calibrate a specific control position"""
        print(f"\n🎯 {position_name.upper()} CALIBRATION")
        print("=" * 50)
        print(f"📋 {instruction}")
        print("   Hold the position steady...")
        
        input("Press ENTER when ready to record this position...")
        
        # Read values
        values = self.read_current_values(20)  # More samples for accuracy
        
        if values['throttle_duty'] > 0:
            print(f"   🚗 Throttle: {values['throttle_duty']:.2f}% duty cycle")
        if values['steering_duty'] > 0:
            print(f"   🎯 Steering: {values['steering_duty']:.2f}% duty cycle")
            
        return values
    
    def run_calibration(self):
        """Run interactive calibration sequence"""
        print("\n🔧 INTERACTIVE PWM CALIBRATION")
        print("=" * 60)
        print("This tool will guide you through calibrating your RC car controls.")
        print("For each position, hold the control steady and press ENTER.")
        print("=" * 60)
        
        # Calibration sequence
        calibration_steps = [
            {
                'name': 'throttle_neutral',
                'instruction': 'Set throttle to NEUTRAL/STOPPED position (no movement)',
                'store_throttle': True
            },
            {
                'name': 'throttle_min',
                'instruction': 'Set throttle to MINIMUM (full brake/reverse if available)',
                'store_throttle': True
            },
            {
                'name': 'throttle_max',
                'instruction': 'Set throttle to MAXIMUM (full forward - be careful!)',
                'store_throttle': True
            },
            {
                'name': 'steering_center',
                'instruction': 'Set steering to CENTER/STRAIGHT position',
                'store_steering': True
            },
            {
                'name': 'steering_left',
                'instruction': 'Turn steering FULL LEFT',
                'store_steering': True
            },
            {
                'name': 'steering_right',
                'instruction': 'Turn steering FULL RIGHT',
                'store_steering': True
            }
        ]
        
        # Run calibration steps
        results = {}
        for step in calibration_steps:
            values = self.calibrate_position(step['name'], step['instruction'])
            
            if step.get('store_throttle') and values['throttle_duty'] > 0:
                results[step['name'] + '_throttle'] = values['throttle_duty']
                
            if step.get('store_steering') and values['steering_duty'] > 0:
                results[step['name'] + '_steering'] = values['steering_duty']
        
        return results
    
    def generate_arduino_code(self, results):
        """Generate updated Arduino calibration constants"""
        print("\n" + "=" * 70)
        print("📊 CALIBRATION RESULTS & ARDUINO CODE UPDATES")
        print("=" * 70)
        
        # Analyze results
        throttle_values = []
        steering_values = []
        
        for key, value in results.items():
            if 'throttle' in key:
                throttle_values.append((key, value))
            elif 'steering' in key:
                steering_values.append((key, value))
        
        print("\n🚗 THROTTLE ANALYSIS:")
        for key, value in throttle_values:
            print(f"   {key.replace('_throttle', '').upper()}: {value:.2f}%")
        
        print("\n🎯 STEERING ANALYSIS:")
        for key, value in steering_values:
            print(f"   {key.replace('_steering', '').upper()}: {value:.2f}%")
        
        # Generate Arduino code
        print("\n🔧 UPDATED ARDUINO CALIBRATION CODE:")
        print("-" * 50)
        print("// Replace the calibration constants in your Arduino code with:")
        print()
        
        if throttle_values:
            # Find min, max, neutral for throttle
            throttle_dict = {k.replace('_throttle', ''): v for k, v in throttle_values}
            t_min = throttle_dict.get('throttle_min', 0)
            t_max = throttle_dict.get('throttle_max', 70)
            t_neutral = throttle_dict.get('throttle_neutral', 0)
            
            print("// Throttle calibration (measured values)")
            print(f"const float THROTTLE_MIN_DUTY = {t_min:.1f};     // Minimum/brake")
            print(f"const float THROTTLE_MAX_DUTY = {t_max:.1f};     // Maximum forward")
            print(f"const float THROTTLE_NEUTRAL_DUTY = {t_neutral:.1f};  // Neutral/stopped")
        
        print()
        
        if steering_values:
            # Find left, right, center for steering
            steering_dict = {k.replace('_steering', ''): v for k, v in steering_values}
            s_left = steering_dict.get('steering_left', 5.0)
            s_right = steering_dict.get('steering_right', 9.2)
            s_center = steering_dict.get('steering_center', 7.0)
            
            print("// Steering calibration (measured values)")
            print(f"const float STEERING_MIN_DUTY = {s_left:.1f};    // Full left")
            print(f"const float STEERING_MAX_DUTY = {s_right:.1f};    // Full right") 
            print(f"const float STEERING_NEUTRAL_DUTY = {s_center:.1f}; // Center/straight")
        
        print()
        print("=" * 70)
        print("✅ Copy these values into your Arduino code and upload!")
        
    def close(self):
        """Close connection"""
        if self.serial_conn:
            self.serial_conn.close()

def main():
    parser = argparse.ArgumentParser(description='Interactive PWM Calibration Tool')
    parser.add_argument('--port', type=str, default='/dev/ttyACM0', help='Arduino serial port')
    parser.add_argument('--baudrate', type=int, default=115200, help='Serial baudrate')
    
    args = parser.parse_args()
    
    calibrator = InteractiveCalibrator(args.port, args.baudrate)
    
    try:
        if calibrator.connect():
            results = calibrator.run_calibration()
            calibrator.generate_arduino_code(results)
        else:
            print("❌ Failed to connect to Arduino")
            
    except KeyboardInterrupt:
        print("\n\n👋 Calibration interrupted")
    finally:
        calibrator.close()

if __name__ == '__main__':
    main()