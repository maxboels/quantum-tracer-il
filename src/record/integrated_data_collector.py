#!/usr/bin/env python3
"""
Integrated Data Collection System for RC Car Imitation Learning
================================================================

This system coordinates:
1. Arduino PWM signal reading via USB serial
2. Camera frame capture with timestamps
3. Synchronized data logging for training episodes

Requirements:
- Arduino running enhanced_pwm_recorder.ino connected via USB
- Camera connected to Raspberry Pi
- Python packages: opencv-python, pyserial, numpy

Usage:
    python3 integrated_data_collector.py --episode-duration 60 --output-dir ./episodes
"""

import argparse
import cv2
import serial
import json
import time
import os
import threading
import queue
from datetime import datetime
from dataclasses import dataclass
from typing import Optional, Tuple, List
import numpy as np

@dataclass
class ControlSample:
    """Single control measurement from Arduino"""
    arduino_timestamp: int  # Arduino millis()
    system_timestamp: float  # Python time.time()
    steering_normalized: float  # [-1.0, 1.0]
    throttle_normalized: float  # [0.0, 1.0]
    steering_raw_us: int
    throttle_raw_us: int
    steering_period_us: int
    throttle_period_us: int

@dataclass
class FrameSample:
    """Single camera frame with metadata"""
    frame_id: int
    timestamp: float
    image_path: str

@dataclass
class EpisodeData:
    """Complete episode data structure"""
    episode_id: str
    start_time: float
    end_time: float
    duration: float
    control_samples: List[ControlSample]
    frame_samples: List[FrameSample]
    metadata: dict

class ArduinoReader:
    """Handles serial communication with Arduino"""
    
    def __init__(self, port: str = '/dev/ttyUSB0', baudrate: int = 115200):
        self.port = port
        self.baudrate = baudrate
        self.serial_conn = None
        self.running = False
        self.data_queue = queue.Queue()
        
    def connect(self) -> bool:
        """Establish serial connection with Arduino"""
        try:
            self.serial_conn = serial.Serial(self.port, self.baudrate, timeout=1)
            time.sleep(2)  # Allow Arduino to reset
            
            # Wait for Arduino ready signal
            while True:
                line = self.serial_conn.readline().decode('utf-8').strip()
                if line == "ARDUINO_READY":
                    print(f"✓ Arduino connected on {self.port}")
                    return True
                    
        except serial.SerialException as e:
            print(f"✗ Failed to connect to Arduino: {e}")
            return False
    
    def start_reading(self):
        """Start reading data in background thread"""
        self.running = True
        self.read_thread = threading.Thread(target=self._read_loop, daemon=True)
        self.read_thread.start()
    
    def stop_reading(self):
        """Stop reading and close connection"""
        self.running = False
        if self.serial_conn:
            self.serial_conn.close()
    
    def _read_loop(self):
        """Background thread for reading serial data"""
        while self.running and self.serial_conn:
            try:
                line = self.serial_conn.readline().decode('utf-8').strip()
                if line.startswith('DATA,'):
                    self._parse_data_line(line)
            except Exception as e:
                print(f"Serial read error: {e}")
                
    def _parse_data_line(self, line: str):
        """Parse incoming data line from Arduino"""
        try:
            parts = line.split(',')
            if len(parts) == 8:  # DATA,timestamp,steer,throttle,steer_raw,throttle_raw,steer_period,throttle_period
                sample = ControlSample(
                    arduino_timestamp=int(parts[1]),
                    system_timestamp=time.time(),
                    steering_normalized=float(parts[2]),
                    throttle_normalized=float(parts[3]),
                    steering_raw_us=int(parts[4]),
                    throttle_raw_us=int(parts[5]),
                    steering_period_us=int(parts[6]),
                    throttle_period_us=int(parts[7])
                )
                self.data_queue.put(sample)
        except (ValueError, IndexError) as e:
            print(f"Data parsing error: {e}")

class CameraCapture:
    """Handles camera frame capture"""
    
    def __init__(self, camera_id: int = 0, fps: int = 30, resolution: Tuple[int, int] = (640, 480), flip_vertically: bool = True):
        self.camera_id = camera_id
        self.fps = fps
        self.resolution = resolution
        self.flip_vertically = flip_vertically
        self.cap = None
        self.running = False
        self.frame_queue = queue.Queue()
        self.frame_counter = 0
        
    def initialize(self) -> bool:
        """Initialize camera"""
        try:
            self.cap = cv2.VideoCapture(self.camera_id)
            self.cap.set(cv2.CAP_PROP_FPS, self.fps)
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.resolution[0])
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.resolution[1])
            
            # Test capture
            ret, frame = self.cap.read()
            if ret:
                print(f"✓ Camera initialized: {self.resolution[0]}x{self.resolution[1]} @ {self.fps}fps")
                return True
            else:
                print("✗ Failed to capture test frame")
                return False
                
        except Exception as e:
            print(f"✗ Camera initialization failed: {e}")
            return False
    
    def start_capture(self):
        """Start capturing frames in background thread"""
        self.running = True
        self.capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.capture_thread.start()
    
    def stop_capture(self):
        """Stop capture and cleanup"""
        self.running = False
        if self.cap:
            self.cap.release()
    
    def _capture_loop(self):
        """Background thread for frame capture"""
        frame_interval = 1.0 / self.fps
        last_frame_time = time.time()
        
        while self.running and self.cap:
            current_time = time.time()
            
            if current_time - last_frame_time >= frame_interval:
                ret, frame = self.cap.read()
                if ret:
                    # Apply vertical flip if requested
                    if self.flip_vertically:
                        frame = cv2.flip(frame, 0)  # 0 = flip around x-axis (vertical flip)
                    
                    self.frame_counter += 1
                    frame_sample = FrameSample(
                        frame_id=self.frame_counter,
                        timestamp=current_time,
                        image_path=""  # Will be set when saved
                    )
                    self.frame_queue.put((frame_sample, frame))
                    last_frame_time = current_time
                else:
                    print("Failed to capture frame")
            
            time.sleep(0.001)  # Small sleep to prevent CPU spinning

class EpisodeRecorder:
    """Coordinates episode recording"""
    
    def __init__(self, output_dir: str, episode_duration: int = 15):
        self.output_dir = output_dir
        self.episode_duration = episode_duration
        self.arduino_reader = ArduinoReader()
        self.camera = CameraCapture()
        
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        
    def record_episode(self) -> bool:
        """Record a single episode"""
        
        # Generate episode ID
        episode_id = datetime.now().strftime("episode_%Y%m%d_%H%M%S")
        episode_dir = os.path.join(self.output_dir, episode_id)
        os.makedirs(episode_dir, exist_ok=True)
        os.makedirs(os.path.join(episode_dir, "frames"), exist_ok=True)
        
        print(f"\n🎬 Starting Episode: {episode_id}")
        print(f"Duration: {self.episode_duration} seconds")
        print("=" * 50)
        
        # Initialize systems
        if not self.arduino_reader.connect():
            return False
            
        if not self.camera.initialize():
            return False
        
        # Start data collection
        self.arduino_reader.start_reading()
        self.camera.start_capture()
        
        # Episode data collection
        control_samples = []
        frame_samples = []
        start_time = time.time()
        end_time = start_time + self.episode_duration
        
        print("🔴 Recording started...")
        
        try:
            while time.time() < end_time:
                current_time = time.time()
                elapsed = current_time - start_time
                remaining = self.episode_duration - elapsed
                
                # Collect control data
                try:
                    while True:
                        control_sample = self.arduino_reader.data_queue.get_nowait()
                        control_samples.append(control_sample)
                except queue.Empty:
                    pass
                
                # Collect frame data
                try:
                    while True:
                        frame_sample, frame = self.camera.frame_queue.get_nowait()
                        
                        # Save frame
                        frame_filename = f"frame_{frame_sample.frame_id:06d}.jpg"
                        frame_path = os.path.join(episode_dir, "frames", frame_filename)
                        cv2.imwrite(frame_path, frame)
                        
                        # Update frame sample with path
                        frame_sample.image_path = os.path.join("frames", frame_filename)
                        frame_samples.append(frame_sample)
                        
                except queue.Empty:
                    pass
                
                # Progress update
                if int(elapsed) % 5 == 0 and elapsed > 0:
                    print(f"⏱️  {elapsed:.0f}s | Controls: {len(control_samples)} | Frames: {len(frame_samples)} | Remaining: {remaining:.0f}s")
                
                time.sleep(0.01)  # Small sleep
        
        except KeyboardInterrupt:
            print("\n⏹️  Recording interrupted by user")
        
        finally:
            # Stop data collection
            self.arduino_reader.stop_reading()
            self.camera.stop_capture()
            
            actual_duration = time.time() - start_time
            
            # Create episode data structure
            episode_data = EpisodeData(
                episode_id=episode_id,
                start_time=start_time,
                end_time=time.time(),
                duration=actual_duration,
                control_samples=control_samples,
                frame_samples=frame_samples,
                metadata={
                    "camera_fps": self.camera.fps,
                    "camera_resolution": self.camera.resolution,
                    "arduino_port": self.arduino_reader.port,
                    "total_control_samples": len(control_samples),
                    "total_frames": len(frame_samples),
                    "avg_control_rate": len(control_samples) / actual_duration if actual_duration > 0 else 0,
                    "avg_frame_rate": len(frame_samples) / actual_duration if actual_duration > 0 else 0
                }
            )
            
            # Save episode metadata
            self._save_episode_data(episode_dir, episode_data)
            
            print(f"\n✅ Episode completed!")
            print(f"📁 Data saved to: {episode_dir}")
            print(f"⏱️  Duration: {actual_duration:.1f}s")
            print(f"🎮 Control samples: {len(control_samples)} ({len(control_samples)/actual_duration:.1f} Hz)")
            print(f"📷 Frame samples: {len(frame_samples)} ({len(frame_samples)/actual_duration:.1f} Hz)")
            
        return True
    
    def _save_episode_data(self, episode_dir: str, episode_data: EpisodeData):
        """Save episode metadata and synchronized data"""
        
        # Convert to serializable format
        episode_dict = {
            "episode_id": episode_data.episode_id,
            "start_time": episode_data.start_time,
            "end_time": episode_data.end_time,
            "duration": episode_data.duration,
            "metadata": episode_data.metadata,
            "control_samples": [
                {
                    "arduino_timestamp": s.arduino_timestamp,
                    "system_timestamp": s.system_timestamp,
                    "steering_normalized": s.steering_normalized,
                    "throttle_normalized": s.throttle_normalized,
                    "steering_raw_us": s.steering_raw_us,
                    "throttle_raw_us": s.throttle_raw_us,
                    "steering_period_us": s.steering_period_us,
                    "throttle_period_us": s.throttle_period_us
                }
                for s in episode_data.control_samples
            ],
            "frame_samples": [
                {
                    "frame_id": f.frame_id,
                    "timestamp": f.timestamp,
                    "image_path": f.image_path
                }
                for f in episode_data.frame_samples
            ]
        }
        
        # Save as JSON
        metadata_path = os.path.join(episode_dir, "episode_data.json")
        with open(metadata_path, 'w') as f:
            json.dump(episode_dict, f, indent=2)
        
        # Also save as CSV for easy analysis
        self._save_csv_format(episode_dir, episode_data)
    
    def _save_csv_format(self, episode_dir: str, episode_data: EpisodeData):
        """Save data in CSV format for analysis"""
        import csv
        
        # Control data CSV
        control_csv_path = os.path.join(episode_dir, "control_data.csv")
        with open(control_csv_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                'arduino_timestamp', 'system_timestamp', 'steering_normalized', 
                'throttle_normalized', 'steering_raw_us', 'throttle_raw_us',
                'steering_period_us', 'throttle_period_us'
            ])
            for sample in episode_data.control_samples:
                writer.writerow([
                    sample.arduino_timestamp, sample.system_timestamp,
                    sample.steering_normalized, sample.throttle_normalized,
                    sample.steering_raw_us, sample.throttle_raw_us,
                    sample.steering_period_us, sample.throttle_period_us
                ])
        
        # Frame data CSV
        frame_csv_path = os.path.join(episode_dir, "frame_data.csv")
        with open(frame_csv_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['frame_id', 'timestamp', 'image_path'])
            for sample in episode_data.frame_samples:
                writer.writerow([
                    sample.frame_id, sample.timestamp, sample.image_path
                ])

def main():
    parser = argparse.ArgumentParser(description='RC Car Episode Data Collector')
    parser.add_argument('--episode-duration', type=int, default=15, help='Episode duration in seconds')
    parser.add_argument('--output-dir', type=str, default='./episodes', help='Output directory for episodes')
    parser.add_argument('--arduino-port', type=str, default='/dev/ttyACM0', help='Arduino serial port')
    parser.add_argument('--camera-id', type=int, default=0, help='Camera device ID')
    
    args = parser.parse_args()
    
    print("RC Car Imitation Learning Data Collector")
    print("=" * 40)
    print(f"Episode Duration: {args.episode_duration}s")
    print(f"Output Directory: {args.output_dir}")
    print(f"Arduino Port: {args.arduino_port}")
    print(f"Camera ID: {args.camera_id}")
    
    recorder = EpisodeRecorder(
        output_dir=args.output_dir,
        episode_duration=args.episode_duration
    )
    
    # Update Arduino reader and camera settings if provided
    recorder.arduino_reader.port = args.arduino_port
    recorder.camera.camera_id = args.camera_id
    recorder.camera.flip_vertically = True # Default to True for upside-down mounting
    
    try:
        episode_num = 1
        while True:
            input(f"\nPress ENTER to start Episode {episode_num} (or Ctrl+C to quit)...")
            
            success = recorder.record_episode()
            if success:
                episode_num += 1
            else:
                print("Episode recording failed. Check connections and try again.")
                
    except KeyboardInterrupt:
        print("\n\n👋 Data collection session ended.")
        print("Thank you for collecting training data!")

if __name__ == '__main__':
    main()