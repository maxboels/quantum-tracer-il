#!/usr/bin/env python3
"""
PWM Diagnostic Tool for RC Car Data Collection
==============================================

This tool validates PWM data reading from the Arduino and identifies issues
with throttle or steering signal processing.

Usage:
    python3 pwm_diagnostic_tool.py --port /dev/ttyUSB0 --duration 30
"""

import argparse
import serial
import time
import sys
from collections import defaultdict, deque
import statistics

class PWMDiagnostic:
    def __init__(self, port='/dev/ttyUSB0', baudrate=115200):
        self.port = port
        self.baudrate = baudrate
        self.serial_conn = None
        
        # Data storage
        self.raw_data = []
        self.steering_data = {'normalized': [], 'raw_us': [], 'period_us': []}
        self.throttle_data = {'normalized': [], 'raw_us': [], 'period_us': []}
        
        # Signal quality tracking
        self.signal_stats = {
            'total_samples': 0,
            'steering_valid': 0,
            'throttle_valid': 0,
            'parse_errors': 0,
            'serial_errors': 0
        }
        
        # Real-time display
        self.recent_samples = deque(maxlen=10)
        
    def connect(self):
        """Connect to Arduino and verify communication"""
        print(f"🔌 Connecting to Arduino on {self.port}...")
        
        try:
            # Try to detect Arduino port if default fails
            if not self._test_port(self.port):
                detected_port = self._detect_arduino_port()
                if detected_port:
                    self.port = detected_port
                    print(f"   Auto-detected Arduino on {self.port}")
                else:
                    print("❌ No Arduino found. Check connection and port.")
                    return False
            
            self.serial_conn = serial.Serial(self.port, self.baudrate, timeout=1)
            time.sleep(2)  # Wait for Arduino reset
            
            # Wait for Arduino ready signal
            print("⏳ Waiting for Arduino initialization...")
            timeout = 10
            start_time = time.time()
            
            while time.time() - start_time < timeout:
                try:
                    line = self.serial_conn.readline().decode('utf-8').strip()
                    if 'ARDUINO_READY' in line:
                        print("✅ Arduino connection established!")
                        return True
                    elif line.startswith('DATA,'):
                        print("✅ Arduino already running - data stream detected!")
                        return True
                except:
                    pass
                    
            print("⚠️  Arduino ready signal not detected, but proceeding...")
            return True
            
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            return False
    
    def _test_port(self, port):
        """Test if a serial port is accessible"""
        try:
            test_conn = serial.Serial(port, self.baudrate, timeout=0.5)
            test_conn.close()
            return True
        except:
            return False
    
    def _detect_arduino_port(self):
        """Try to detect Arduino on common ports"""
        import serial.tools.list_ports
        
        for port in serial.tools.list_ports.comports():
            if any(keyword in port.description.lower() for keyword in ['arduino', 'ch340', 'ftdi', 'usb']):
                if self._test_port(port.device):
                    return port.device
        
        # Try common ports
        for port_name in ['/dev/ttyUSB0', '/dev/ttyUSB1', '/dev/ttyACM0', '/dev/ttyACM1']:
            if self._test_port(port_name):
                return port_name
                
        return None
    
    def run_diagnostic(self, duration=30):
        """Run comprehensive PWM diagnostic"""
        if not self.serial_conn:
            print("❌ Not connected to Arduino")
            return False
            
        print(f"\n🔍 Starting {duration}-second PWM diagnostic...")
        print("📋 INSTRUCTIONS:")
        print("   1. Turn ON your RC transmitter")
        print("   2. Test STEERING: Move left → center → right")
        print("   3. Test THROTTLE: Move brake → neutral → forward")
        print("   4. Repeat movements to test consistency")
        print("=" * 60)
        
        start_time = time.time()
        last_report = start_time
        sample_count = 0
        
        try:
            while (time.time() - start_time) < duration:
                current_time = time.time()
                
                # Read and process data
                try:
                    if self.serial_conn.in_waiting > 0:
                        line = self.serial_conn.readline().decode('utf-8').strip()
                        if line:
                            self._process_line(line)
                            sample_count += 1
                
                except serial.SerialException as e:
                    self.signal_stats['serial_errors'] += 1
                    print(f"⚠️ Serial error: {e}")
                    
                # Real-time reporting every 3 seconds
                if current_time - last_report >= 3.0:
                    self._print_realtime_status(current_time - start_time, sample_count)
                    last_report = current_time
                    
                time.sleep(0.01)  # Small delay to prevent CPU overload
                
        except KeyboardInterrupt:
            print("\n🛑 Diagnostic interrupted by user")
            
        print(f"\n✅ Diagnostic complete! Processed {sample_count} samples in {duration}s")
        self._generate_report()
        return True
    
    def _process_line(self, line):
        """Process a single data line from Arduino"""
        self.raw_data.append(line)
        
        try:
            if line.startswith('DATA,'):
                # Parse: DATA,timestamp,steering_norm,throttle_norm,steering_raw,throttle_raw,steering_period,throttle_period
                parts = line.split(',')
                if len(parts) >= 8:
                    timestamp = int(parts[1])
                    steer_norm = float(parts[2])
                    throttle_norm = float(parts[3])
                    steer_raw = int(parts[4])
                    throttle_raw = int(parts[5])
                    steer_period = int(parts[6])
                    throttle_period = int(parts[7])
                    
                    # Store data
                    self.steering_data['normalized'].append(steer_norm)
                    self.steering_data['raw_us'].append(steer_raw)
                    self.steering_data['period_us'].append(steer_period)
                    
                    self.throttle_data['normalized'].append(throttle_norm)
                    self.throttle_data['raw_us'].append(throttle_raw)
                    self.throttle_data['period_us'].append(throttle_period)
                    
                    # Track signal validity
                    if steer_raw > 0 and steer_period > 1000:
                        self.signal_stats['steering_valid'] += 1
                    if throttle_raw > 0 and throttle_period > 100:
                        self.signal_stats['throttle_valid'] += 1
                        
                    self.signal_stats['total_samples'] += 1
                    
                    # Store recent sample for real-time display
                    sample = {
                        'steering': {'norm': steer_norm, 'raw': steer_raw, 'period': steer_period},
                        'throttle': {'norm': throttle_norm, 'raw': throttle_raw, 'period': throttle_period}
                    }
                    self.recent_samples.append(sample)
                    
                else:
                    self.signal_stats['parse_errors'] += 1
                    
        except (ValueError, IndexError) as e:
            self.signal_stats['parse_errors'] += 1
    
    def _print_realtime_status(self, runtime, samples):
        """Print real-time diagnostic status"""
        print(f"\n--- Status @ {runtime:.1f}s (Samples: {samples}) ---")
        
        if self.recent_samples:
            latest = self.recent_samples[-1]
            
            # Current values
            print(f"🎯 STEERING: {latest['steering']['norm']:+6.3f} | Raw: {latest['steering']['raw']:4d}µs | Period: {latest['steering']['period']:5d}µs")
            print(f"🚗 THROTTLE: {latest['throttle']['norm']:+6.3f} | Raw: {latest['throttle']['raw']:4d}µs | Period: {latest['throttle']['period']:5d}µs")
            
            # Recent trends (last 5 samples)
            if len(self.recent_samples) >= 5:
                recent_steer = [s['steering']['norm'] for s in list(self.recent_samples)[-5:]]
                recent_throttle = [s['throttle']['norm'] for s in list(self.recent_samples)[-5:]]
                
                steer_range = max(recent_steer) - min(recent_steer)
                throttle_range = max(recent_throttle) - min(recent_throttle)
                
                print(f"📊 Recent Activity - Steering: {steer_range:.3f} | Throttle: {throttle_range:.3f}")
        
        # Signal quality
        total = self.signal_stats['total_samples']
        if total > 0:
            steer_quality = (self.signal_stats['steering_valid'] / total) * 100
            throttle_quality = (self.signal_stats['throttle_valid'] / total) * 100
            print(f"📡 Signal Quality - Steering: {steer_quality:.1f}% | Throttle: {throttle_quality:.1f}%")
    
    def _generate_report(self):
        """Generate comprehensive diagnostic report"""
        print("\n" + "="*70)
        print("📊 PWM DIAGNOSTIC REPORT")
        print("="*70)
        
        if self.signal_stats['total_samples'] == 0:
            print("❌ NO DATA RECEIVED!")
            print("   Troubleshooting:")
            print("   • Check Arduino is powered and running pwm_recorder.ino")
            print("   • Verify USB connection")
            print("   • Check serial port (try ls /dev/ttyUSB* /dev/ttyACM*)")
            return
        
        total = self.signal_stats['total_samples']
        
        print(f"📈 SAMPLE STATISTICS:")
        print(f"   Total samples: {total}")
        print(f"   Steering valid: {self.signal_stats['steering_valid']} ({self.signal_stats['steering_valid']/total*100:.1f}%)")
        print(f"   Throttle valid: {self.signal_stats['throttle_valid']} ({self.signal_stats['throttle_valid']/total*100:.1f}%)")
        print(f"   Parse errors: {self.signal_stats['parse_errors']}")
        print(f"   Serial errors: {self.signal_stats['serial_errors']}")
        
        # Analyze steering
        print(f"\n🎯 STEERING ANALYSIS:")
        if self.steering_data['normalized']:
            steer_norm_min = min(self.steering_data['normalized'])
            steer_norm_max = max(self.steering_data['normalized'])
            steer_raw_min = min([x for x in self.steering_data['raw_us'] if x > 0])
            steer_raw_max = max(self.steering_data['raw_us'])
            
            print(f"   Normalized range: {steer_norm_min:.3f} to {steer_norm_max:.3f}")
            print(f"   Raw pulse range: {steer_raw_min}µs to {steer_raw_max}µs")
            print(f"   Status: {'✅ GOOD' if steer_norm_max - steer_norm_min > 0.5 else '⚠️ LIMITED RANGE'}")
        else:
            print("   ❌ NO VALID STEERING DATA")
        
        # Analyze throttle
        print(f"\n🚗 THROTTLE ANALYSIS:")
        if self.throttle_data['normalized']:
            throttle_norm_min = min(self.throttle_data['normalized'])
            throttle_norm_max = max(self.throttle_data['normalized'])
            throttle_raw_min = min([x for x in self.throttle_data['raw_us'] if x > 0])
            throttle_raw_max = max(self.throttle_data['raw_us'])
            
            print(f"   Normalized range: {throttle_norm_min:.3f} to {throttle_norm_max:.3f}")
            print(f"   Raw pulse range: {throttle_raw_min}µs to {throttle_raw_max}µs")
            
            # Throttle-specific diagnostics
            if throttle_norm_max < 0.1:
                print("   ❌ THROTTLE ISSUE: No forward throttle detected")
                print("      • Check throttle PWM wiring to Arduino pin 2")
                print("      • Verify RC transmitter throttle channel")
                print("      • Test with manual throttle movement")
            else:
                print(f"   ✅ THROTTLE OK: Range {throttle_norm_max - throttle_norm_min:.3f}")
        else:
            print("   ❌ NO VALID THROTTLE DATA")
            print("      • Check Arduino pin 2 connection")
            print("      • Verify throttle PWM signal from ESC/Receiver")
        
        # Recommendations
        print(f"\n🔧 RECOMMENDATIONS:")
        steer_ok = len(self.steering_data['normalized']) > 0 and (max(self.steering_data['normalized']) - min(self.steering_data['normalized'])) > 0.5
        throttle_ok = len(self.throttle_data['normalized']) > 0 and max(self.throttle_data['normalized']) > 0.1
        
        if steer_ok and throttle_ok:
            print("   ✅ Both steering and throttle look good!")
            print("   ➡️  Ready to run integrated_data_collector.py")
        elif steer_ok and not throttle_ok:
            print("   ⚠️  Steering OK, but throttle needs attention")
            print("   ➡️  Fix throttle wiring before data collection")
        elif not steer_ok and throttle_ok:
            print("   ⚠️  Throttle OK, but steering needs attention")
            print("   ➡️  Fix steering wiring before data collection")
        else:
            print("   ❌ Both channels need attention")
            print("   ➡️  Check all PWM connections and RC transmitter")
    
    def close(self):
        """Close serial connection"""
        if self.serial_conn:
            self.serial_conn.close()

def main():
    parser = argparse.ArgumentParser(description='PWM Diagnostic Tool')
    parser.add_argument('--port', type=str, default='/dev/ttyUSB0', help='Arduino serial port')
    parser.add_argument('--duration', type=int, default=30, help='Diagnostic duration in seconds')
    parser.add_argument('--baudrate', type=int, default=115200, help='Serial baudrate')
    
    args = parser.parse_args()
    
    print("🔧 PWM Diagnostic Tool for RC Car Data Collection")
    print("=" * 50)
    
    diagnostic = PWMDiagnostic(args.port, args.baudrate)
    
    try:
        if diagnostic.connect():
            diagnostic.run_diagnostic(args.duration)
        else:
            print("❌ Failed to connect to Arduino")
            print("   Check:")
            print("   • Arduino is connected via USB")
            print("   • Correct serial port (try: ls /dev/ttyUSB* /dev/ttyACM*)")
            print("   • pwm_recorder.ino is uploaded and running")
            
    except KeyboardInterrupt:
        print("\n👋 Diagnostic interrupted")
    finally:
        diagnostic.close()

if __name__ == '__main__':
    main()