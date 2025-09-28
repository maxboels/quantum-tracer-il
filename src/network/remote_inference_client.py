#!/usr/bin/env python3
"""
Remote Inference Client (Raspberry Pi Side)
===========================================

Streams camera frames and sensor data to a remote inference server (laptop),
receives control commands, and executes them on the RC car.

This replaces the episode recorder for live autonomous driving.

Architecture:
    Raspberry Pi → WiFi → Laptop (GPU Inference) → WiFi → Raspberry Pi → Arduino → RC Car

Usage:
    python3 remote_inference_client.py --server-ip 192.168.1.100 --server-port 8888
"""

import argparse
import cv2
import serial
import socket
import json
import time
import threading
import queue
import numpy as np
from dataclasses import dataclass, asdict
from typing import Optional, Tuple
import struct
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class SensorData:
    """Current sensor reading from Arduino"""
    timestamp: float
    steering_current: float  # Current steering position [-1, 1]
    throttle_current: float  # Current throttle position [0, 1]
    arduino_timestamp: int

@dataclass
class ControlCommand:
    """Control command from inference server"""
    timestamp: float
    steering_target: float   # Target steering [-1, 1]
    throttle_target: float   # Target throttle [0, 1]
    confidence: float        # Model confidence [0, 1]

class ArduinoInterface:
    """Enhanced Arduino interface with control output capability"""
    
    def __init__(self, port: str = '/dev/ttyACM0', baudrate: int = 115200):
        self.port = port
        self.baudrate = baudrate
        self.serial_conn = None
        self.running = False
        self.sensor_queue = queue.Queue()
        
    def connect(self) -> bool:
        """Connect to Arduino"""
        try:
            self.serial_conn = serial.Serial(self.port, self.baudrate, timeout=1)
            time.sleep(2)  # Arduino reset
            
            # Wait for Arduino ready
            while True:
                line = self.serial_conn.readline().decode('utf-8').strip()
                if line == "ARDUINO_READY":
                    logger.info(f"✓ Arduino connected on {self.port}")
                    return True
                    
        except Exception as e:
            logger.error(f"Arduino connection failed: {e}")
            return False
    
    def start_reading(self):
        """Start sensor data reading"""
        self.running = True
        self.read_thread = threading.Thread(target=self._read_loop, daemon=True)
        self.read_thread.start()
    
    def stop_reading(self):
        """Stop reading"""
        self.running = False
        if self.serial_conn:
            self.serial_conn.close()
    
    def send_control_command(self, steering: float, throttle: float):
        """Send control command to Arduino"""
        if not self.serial_conn:
            return False
            
        try:
            # Send control command (this would need Arduino firmware modification)
            command = f"CTRL,{steering:.4f},{throttle:.4f}\n"
            self.serial_conn.write(command.encode())
            return True
        except Exception as e:
            logger.error(f"Control send error: {e}")
            return False
    
    def _read_loop(self):
        """Background sensor reading"""
        while self.running and self.serial_conn:
            try:
                line = self.serial_conn.readline().decode('utf-8').strip()
                if line.startswith('DATA,'):
                    self._parse_sensor_data(line)
            except Exception as e:
                logger.error(f"Sensor read error: {e}")
    
    def _parse_sensor_data(self, line: str):
        """Parse Arduino sensor data"""
        try:
            parts = line.split(',')
            if len(parts) >= 8:
                sensor_data = SensorData(
                    timestamp=time.time(),
                    steering_current=float(parts[2]),
                    throttle_current=float(parts[3]),
                    arduino_timestamp=int(parts[1])
                )
                self.sensor_queue.put(sensor_data)
        except Exception as e:
            logger.error(f"Sensor parsing error: {e}")

class CameraStreamer:
    """Camera capture for remote streaming"""
    
    def __init__(self, camera_id: int = 0, fps: int = 30, resolution: Tuple[int, int] = (320, 240)):
        self.camera_id = camera_id
        self.fps = fps
        self.resolution = resolution
        self.cap = None
        self.running = False
        self.frame_queue = queue.Queue(maxsize=5)  # Limit queue size for low latency
        
    def initialize(self) -> bool:
        """Initialize camera"""
        try:
            self.cap = cv2.VideoCapture(self.camera_id)
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.resolution[0])
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.resolution[1])
            self.cap.set(cv2.CAP_PROP_FPS, self.fps)
            
            # Test capture
            ret, frame = self.cap.read()
            if ret:
                logger.info(f"✓ Camera initialized: {frame.shape}")
                return True
            else:
                logger.error("Camera test capture failed")
                return False
                
        except Exception as e:
            logger.error(f"Camera initialization failed: {e}")
            return False
    
    def start_capture(self):
        """Start frame capture"""
        self.running = True
        self.capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.capture_thread.start()
    
    def stop_capture(self):
        """Stop capture"""
        self.running = False
        if self.cap:
            self.cap.release()
    
    def _capture_loop(self):
        """Background frame capture"""
        while self.running and self.cap:
            ret, frame = self.cap.read()
            if ret:
                # Add to queue, drop old frames if queue is full
                try:
                    self.frame_queue.put_nowait((time.time(), frame))
                except queue.Full:
                    try:
                        self.frame_queue.get_nowait()  # Drop oldest
                        self.frame_queue.put_nowait((time.time(), frame))
                    except queue.Empty:
                        pass
            time.sleep(1.0 / self.fps)

class InferenceClient:
    """Network client for remote inference"""
    
    def __init__(self, server_ip: str, server_port: int = 8888):
        self.server_ip = server_ip
        self.server_port = server_port
        self.socket = None
        self.connected = False
        
    def connect(self) -> bool:
        """Connect to inference server"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(10.0)
            self.socket.connect((self.server_ip, self.server_port))
            self.connected = True
            logger.info(f"✓ Connected to inference server {self.server_ip}:{self.server_port}")
            return True
            
        except Exception as e:
            logger.error(f"Server connection failed: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from server"""
        self.connected = False
        if self.socket:
            self.socket.close()
    
    def send_frame_and_sensors(self, frame: np.ndarray, sensor_data: SensorData) -> Optional[ControlCommand]:
        """Send frame + sensor data, receive control command"""
        if not self.connected:
            return None
            
        try:
            # Encode frame as JPEG
            _, encoded_frame = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            frame_data = encoded_frame.tobytes()
            
            # Create message
            message = {
                'timestamp': time.time(),
                'frame_size': len(frame_data),
                'sensor_data': asdict(sensor_data)
            }
            
            # Send message header
            header = json.dumps(message).encode()
            header_size = len(header)
            
            self.socket.send(struct.pack('I', header_size))
            self.socket.send(header)
            self.socket.send(frame_data)
            
            # Receive response
            response_size = struct.unpack('I', self._recv_exact(4))[0]
            response_data = self._recv_exact(response_size)
            response = json.loads(response_data.decode())
            
            # Parse control command
            if 'control_command' in response:
                cmd_data = response['control_command']
                return ControlCommand(
                    timestamp=cmd_data['timestamp'],
                    steering_target=cmd_data['steering_target'],
                    throttle_target=cmd_data['throttle_target'],
                    confidence=cmd_data.get('confidence', 0.0)
                )
                
        except Exception as e:
            logger.error(f"Communication error: {e}")
            self.connected = False
            return None
    
    def _recv_exact(self, size: int) -> bytes:
        """Receive exactly 'size' bytes"""
        data = b''
        while len(data) < size:
            chunk = self.socket.recv(size - len(data))
            if not chunk:
                raise ConnectionError("Connection closed by server")
            data += chunk
        return data

class RemoteInferenceController:
    """Main controller for remote inference"""
    
    def __init__(self, server_ip: str, server_port: int = 8888, arduino_port: str = '/dev/ttyACM0'):
        self.arduino = ArduinoInterface(arduino_port)
        self.camera = CameraStreamer()
        self.inference_client = InferenceClient(server_ip, server_port)
        
        self.running = False
        self.stats = {
            'frames_sent': 0,
            'commands_received': 0,
            'last_command_time': 0,
            'avg_latency': 0.0
        }
        
    def initialize(self) -> bool:
        """Initialize all systems"""
        logger.info("🚀 Initializing Remote Inference System...")
        
        if not self.arduino.connect():
            return False
            
        if not self.camera.initialize():
            return False
            
        if not self.inference_client.connect():
            return False
            
        logger.info("✓ All systems initialized")
        return True
    
    def start_autonomous_driving(self):
        """Start autonomous driving mode"""
        if not self.running:
            logger.info("🤖 Starting Autonomous Driving Mode...")
            self.running = True
            
            self.arduino.start_reading()
            self.camera.start_capture()
            
            # Main inference loop
            self._inference_loop()
    
    def stop_autonomous_driving(self):
        """Stop autonomous driving"""
        logger.info("⏹️ Stopping Autonomous Driving...")
        self.running = False
        
        self.arduino.stop_reading()
        self.camera.stop_capture()
        self.inference_client.disconnect()
    
    def _inference_loop(self):
        """Main inference loop"""
        logger.info("🔄 Starting inference loop...")
        
        last_stats_time = time.time()
        latencies = []
        
        try:
            while self.running:
                # Get latest frame
                try:
                    frame_timestamp, frame = self.camera.frame_queue.get(timeout=0.1)
                except queue.Empty:
                    continue
                
                # Get latest sensor data
                sensor_data = None
                try:
                    while True:
                        sensor_data = self.arduino.sensor_queue.get_nowait()
                except queue.Empty:
                    if sensor_data is None:
                        continue  # No sensor data available
                
                # Send to inference server
                start_time = time.time()
                control_command = self.inference_client.send_frame_and_sensors(frame, sensor_data)
                
                if control_command:
                    # Calculate latency
                    latency = time.time() - start_time
                    latencies.append(latency)
                    
                    # Send control to Arduino
                    self.arduino.send_control_command(
                        control_command.steering_target,
                        control_command.throttle_target
                    )
                    
                    self.stats['commands_received'] += 1
                    self.stats['last_command_time'] = time.time()
                
                self.stats['frames_sent'] += 1
                
                # Print stats every 5 seconds
                if time.time() - last_stats_time > 5.0:
                    if latencies:
                        self.stats['avg_latency'] = np.mean(latencies)
                        latencies = []
                    
                    logger.info(f"📊 Stats: Frames={self.stats['frames_sent']}, "
                              f"Commands={self.stats['commands_received']}, "
                              f"Latency={self.stats['avg_latency']:.3f}s")
                    last_stats_time = time.time()
                
        except KeyboardInterrupt:
            logger.info("Interrupted by user")
        except Exception as e:
            logger.error(f"Inference loop error: {e}")

def main():
    parser = argparse.ArgumentParser(description='Remote Inference Client (Raspberry Pi)')
    parser.add_argument('--server-ip', type=str, required=True, help='Inference server IP address')
    parser.add_argument('--server-port', type=int, default=8888, help='Server port')
    parser.add_argument('--arduino-port', type=str, default='/dev/ttyACM0', help='Arduino serial port')
    parser.add_argument('--camera-id', type=int, default=0, help='Camera device ID')
    
    args = parser.parse_args()
    
    print("🚗 RC Car Remote Inference Client")
    print("=" * 40)
    print(f"Server: {args.server_ip}:{args.server_port}")
    print(f"Arduino: {args.arduino_port}")
    print(f"Camera: {args.camera_id}")
    
    controller = RemoteInferenceController(
        server_ip=args.server_ip,
        server_port=args.server_port,
        arduino_port=args.arduino_port
    )
    
    try:
        if controller.initialize():
            print("\n✓ Ready for autonomous driving!")
            input("Press ENTER to start autonomous driving (Ctrl+C to stop)...")
            controller.start_autonomous_driving()
        else:
            print("❌ Initialization failed!")
            
    except KeyboardInterrupt:
        print("\n👋 Shutting down...")
    finally:
        controller.stop_autonomous_driving()

if __name__ == '__main__':
    main()